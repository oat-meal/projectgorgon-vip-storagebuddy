{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (ps: with ps; [
      flask
      flask-cors
      pywebview
      pygobject3
      beautifulsoup4
      requests
      pyinstaller
    ]))
    # System dependencies for pywebview on Linux
    gtk3
    webkitgtk_4_1
    gobject-introspection
  ];

  shellHook = ''
    echo "Project Gorgon VIP StorageBuddy Environment"
    echo "Flask is ready!"
    echo ""
    echo "To start the server, run:"
    echo "  python3 web_server.py"
  '';
}
