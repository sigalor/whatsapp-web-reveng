const request = require("request-promise-native");
const acorn = require("acorn");
const walk = require("acorn-walk");

const objectToArray = obj => Object.keys(obj).map(k => [k, obj[k]]);
const indent = (lines, n) => lines.map(l => " ".repeat(n) + l);

async function findAppModules(mods) {
    const ua = { headers: { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0" } }
    const WAWebMain = "https://web.whatsapp.com";
    const index = await request.get(WAWebMain, ua);
    const appPathId = index.match(/data-app="\/app.([0-9a-z]{10,}).js"/)[1]
    const data = await request.get(WAWebMain + "/app." + appPathId + ".js", ua)
    const appModules = acorn.parse(data).body[0].expression.argument.arguments[0].properties;
    return appModules.filter(m => mods.indexOf(m.key.name) != -1);
}

(async () => {
    const wantedModules = ['bgiachiigg', 'bfifcddbbg', 'bbcaggdbc'];
    const unsortedModules = await findAppModules(wantedModules);
    if(unsortedModules.length !== wantedModules.length)
        throw "did not find all wanted modules";
    // Sort modules so that whatsapp module id changes don't change the order in the output protobuf schema
    const modules = []
    for (const mod of wantedModules) {
        modules.push(unsortedModules.find(node => node.key.name === mod))
    }
    
    // find aliases of cross references between the wanted modules
    let modulesInfo = {};
    modules.forEach(({key, value}) => {
        const requiringParam = value.params[2].name;
        modulesInfo[key.name] = { crossRefs: [] };
        walk.simple(value, {
            VariableDeclarator(node) {
                if(node.init && node.init.type === "CallExpression" && node.init.callee.name === requiringParam && node.init.arguments.length == 1 && wantedModules.indexOf(node.init.arguments[0].value) != -1)
                    modulesInfo[key.name].crossRefs.push({ alias: node.id.name, module: node.init.arguments[0].value });
            }
        });
    });

    // find all identifiers and, for enums, their array of values
    for(const mod of modules) {
        let modInfo = modulesInfo[mod.key.name];
        
        // all identifiers will be initialized to "void 0" (i.e. "undefined") at the start, so capture them here
        walk.ancestor(mod, {
            UnaryExpression(node, anc) {
                if(!modInfo.identifiers && node.operator === "void") {
                    let assignments = [], i = 1;
                    anc.reverse();
                    while(anc[i].type === "AssignmentExpression")
                        assignments.push(anc[i++].left);
                        modInfo.identifiers = assignments.map(a => a.property.name).reverse()
                            .reduce((prev, curr) => (prev[curr] = {}, prev), {});
                }
            }
        });
        const enumAliases = {}
        // enums are defined directly, and both enums and messages get a one-letter alias
        walk.simple(mod, {
            AssignmentExpression(node) {
                if (node.left.type === "MemberExpression" && modInfo.identifiers[node.left.property.name]) {
                    let ident = modInfo.identifiers[node.left.property.name];
                    ident.alias = node.right.name;
                    ident.enumValues = enumAliases[ident.alias];
                }
            },
            VariableDeclarator(node) {
                if(node.init && node.init.type === "CallExpression" && node.init.callee.type === "MemberExpression" && node.init.arguments.length === 1 && node.init.arguments[0].type === "ObjectExpression") {
                    enumAliases[node.id.name] = node.init.arguments[0].properties.map(p => ({ name: p.key.name, id: p.value.value }));
                }
            }
        });
    };

    // find the contents for all protobuf messages
    for(const mod of modules) {
        let modInfo = modulesInfo[mod.key.name];

        // message specifications are stored in a "_spec" attribute of the respective identifier alias
        walk.simple(mod, {
            AssignmentExpression(node) {
                if(node.left.type === "MemberExpression" && node.left.property.name === "internalSpec" && node.right.type === "ObjectExpression") {
                    let targetIdentName = Object.keys(modInfo.identifiers).find(k => modInfo.identifiers[k].alias == node.left.object.name);
                    if(!targetIdentName) {
                        console.warn(`found message specification for unknown identifier alias: ${node.left.object.name}`);
                        return;
                    }

                    // partition spec properties by normal members and constraints (like "__oneofs__") which will be processed afterwards
                    let targetIdent = modInfo.identifiers[targetIdentName];
                    let constraints = [], members = [];
                    for(let p of node.right.properties) {
                        p.key.name = p.key.type === "Identifier" ? p.key.name : p.key.value;
                        (p.key.name.substr(0, 2) === "__" ? constraints : members).push(p);
                    }
                    
                    members = members.map(({key: {name}, value: {elements}}) => {
                        let type, flags = [];
                        let unwrapBinaryOr = n => (n.type === "BinaryExpression" && n.operator === "|") ? [].concat(unwrapBinaryOr(n.left), unwrapBinaryOr(n.right)) : [n];

                        // find type and flags
                        unwrapBinaryOr(elements[1]).forEach(m => {
                            if(m.type === "MemberExpression" && m.object.type === "MemberExpression") {
                                if(m.object.property.name === "TYPES")
                                    type = m.property.name.toLowerCase();
                                else if(m.object.property.name === "FLAGS")
                                    flags.push(m.property.name.toLowerCase());
                            }
                        });

                        // determine cross reference name from alias if this member has type "message" or "enum"
                        if(type === "message" || type === "enum") {
                            const currLoc = ` from member '${name}' of message '${targetIdentName}'`;
                            if(elements[2].type === "Identifier") {
                                type = objectToArray(modInfo.identifiers).find(i => i[1].alias === elements[2].name);
                                type ? (type = type[0]) : console.warn(`unable to find reference of alias '${elements[2].name}'` + currLoc);
                            } else if(elements[2].type === "MemberExpression") {
                                let crossRef = modInfo.crossRefs.find(r => r.alias === elements[2].object.name);
                                if(crossRef && modulesInfo[crossRef.module].identifiers[elements[2].property.name])
                                    type = elements[2].property.name;
                                else
                                    console.warn(`unable to find reference of alias to other module '${elements[2].object.name}' or to message ${elements[2].property.name} of this module` + currLoc)
                            }
                        }

                        return { name, id: elements[0].value, type, flags };
                    });

                    // resolve constraints for members
                    constraints.forEach(c => {
                        if(c.key.name === "__oneofs__" && c.value.type === "ObjectExpression") {
                            let newOneOfs = c.value.properties.map(p => ({
                                name: p.key.name,
                                type: "__oneof__",
                                members: p.value.elements.map(e => {
                                    let idx = members.findIndex(m => m.name == e.value);
                                    let member = members[idx];
                                    members.splice(idx, 1);
                                    return member;
                                })
                            }));
                            members = members.concat(newOneOfs);
                        }
                    });

                    targetIdent.members = members;
                }
            }
        });
    };

    // make all enums only one message uses be local to that message
    for(const mod of modules) {
        let idents = modulesInfo[mod.key.name].identifiers;
        let identsArr = objectToArray(idents);

        identsArr.filter(i => !!i[1].enumValues).forEach(e => {
            // count number of occurrences of this enumeration and store these identifiers
            let occurrences = [];
            identsArr.forEach(i => {
                if(i[1].members && i[1].members.find(m => m.type === e[0]))
                    occurrences.push(i[0]);
            });
            
            // if there's only one occurrence, add the enum to that message. Also remove enums that do not occur anywhere
            if(occurrences.length <= 1) {
                if(occurrences.length == 1)
                    idents[occurrences[0]].members.find(m => m.type === e[0]).enumValues = e[1].enumValues;
                delete idents[e[0]];
            }
        });
    }

	console.log('syntax = "proto2";')
	console.log('package proto;')
	console.log('')
    for(const mod of modules) {
        let modInfo = modulesInfo[mod.key.name];
        let spacesPerIndentLevel = 4;

        // enum stringifying function
        let stringifyEnum = (name, values) =>
            [].concat(
                [`enum ${name} {`],
                indent(values.map(v => `${v.name} = ${v.id};`), spacesPerIndentLevel),
                ["}"]
            );

        // message specification member stringifying function
        let stringifyMessageSpecMember = (info, completeFlags = true) => {
            if(info.type === "__oneof__") {
                return [].concat(
                    [`oneof ${info.name} {`],
                    indent([].concat(...info.members.map(m => stringifyMessageSpecMember(m, false))), spacesPerIndentLevel),
                    ["}"]
                );
            } else {
                if(completeFlags && info.flags.length == 0)
                    info.flags.push("optional");
                let ret = info.enumValues ? stringifyEnum(info.type, info.enumValues) : [];
                ret.push(`${info.flags.join(" ") + (info.flags.length == 0 ? "" : " ")}${info.type} ${info.name} = ${info.id};`);
                return ret;
            }
        };

        // message specification stringifying function
        let stringifyMessageSpec = (name, members) =>
            [].concat(
                [`message ${name} {`],
                indent([].concat(...members.map(m => stringifyMessageSpecMember(m))), spacesPerIndentLevel),
                ["}", ""]
            );

        let lines = [].concat(...objectToArray(modInfo.identifiers).map(i => i[1].members ? stringifyMessageSpec(i[0], i[1].members) : stringifyEnum(i[0], i[1].enumValues)));
        console.log(lines.join("\n"));
    }
    
    //console.log(JSON.stringify(modulesInfo, null, 2));
})();
