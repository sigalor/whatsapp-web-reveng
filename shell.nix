with import <nixpkgs> {};
let
  pythonEnv = python27.withPackages (ps: [
    ps.websocket_client
    ps.curve25519-donna
    ps.pycrypto
    ps.pyqrcode
    ps.protobuf
    ps.simple-websocket-server
  ]);
in mkShell {
  buildInputs = [
    pythonEnv
    nodejs-13_x
  ];
  shellHook = ''
    echo "Installing node modules"
    npm ci
    echo "Done."

    echo '
$$\      $$\ $$\                  $$\
$$ | $\  $$ |$$ |                 $$ |
$$ |$$$\ $$ |$$$$$$$\   $$$$$$\ $$$$$$\    $$$$$$$\  $$$$$$\   $$$$$$\   $$$$$$\
$$ $$ $$\$$ |$$  __$$\  \____$$\\_$$  _|  $$  _____| \____$$\ $$  __$$\ $$  __$$\
$$$$  _$$$$ |$$ |  $$ | $$$$$$$ | $$ |    \$$$$$$\   $$$$$$$ |$$ /  $$ |$$ /  $$ |
$$$  / \$$$ |$$ |  $$ |$$  __$$ | $$ |$$\  \____$$\ $$  __$$ |$$ |  $$ |$$ |  $$ |
$$  /   \$$ |$$ |  $$ |\$$$$$$$ | \$$$$  |$$$$$$$  |\$$$$$$$ |$$$$$$$  |$$$$$$$  |
\__/     \__|\__|  \__| \_______|  \____/ \_______/  \_______|$$  ____/ $$  ____/
                                                              $$ |      $$ |
                                                              $$ |      $$ |
                                                              \__|      \__|'
    echo "Node $(node --version)"
    echo "$(python --version)"
    echo "Try running server with: npm start"
  '';
}
