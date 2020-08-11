let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.1.0";
  });

  customizedPython = mach-nix.mkPython {
    requirements = ''
      numpy
      SimpleITK
    '';

    providers = {
      numpy = "nixpkgs";
    };
  };

  pkgs = mach-nix.nixpkgs.pkgs;
in pkgs.mkShell {
  name = "jacob";
  buildInputs = with pkgs; [ customizedPython feh ];
}
