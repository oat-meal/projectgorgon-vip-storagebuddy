{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (ps: with ps; [
      flask
    ]))
  ];

  shellHook = ''
    echo "Project Gorgon VIP Quest Tracker Environment"
    echo "Flask is ready!"
    echo ""
    echo "To start the server, run:"
    echo "  python3 web_server.py"
  '';
}
