{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (ps: with ps; [
      flask
      pywebview
      pygobject3
    ]))
    # System dependencies for pywebview on Linux
    gtk3
    webkitgtk_4_1
    gobject-introspection
  ];

  shellHook = ''
    echo "Project Gorgon VIP Quest Helper Environment"
    echo "Flask is ready!"
    echo ""
    echo "To start the server, run:"
    echo "  python3 web_server.py"
  '';
}
