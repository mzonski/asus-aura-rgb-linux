{
  description = "ASUS Aura RGB Controler reversing";

  inputs = {
    devenv-root = {
      url = "file+file:///dev/null";
      flake = false;
    };
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    devenv.url = "github:cachix/devenv";
    nix2container.url = "github:nlewo/nix2container";
    nix2container.inputs.nixpkgs.follows = "nixpkgs";
    mk-shell-bin.url = "github:rrbutani/nix-mk-shell-bin";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs =
    inputs@{ flake-parts, devenv-root, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        inputs.devenv.flakeModule
      ];
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      perSystem =
        {
          self',
          inputs',
          pkgs,
          system,
          ...
        }:
        {
          devenv.shells.default = {
            name = "asus-aura-rgb-linux";

            packages = with pkgs; [
              python313
              libusb1
              hidapi
            ];

            languages.python = {
              enable = true;
              package = pkgs.python313;
              venv.enable = true;
              venv.requirements = ''
                pyusb>=1.3.1
                hid>=1.0.8

                black>=25.9.0
                isort>=6.0.1
                mypy>=1.18.2
                pylint>=3.3.8
              '';
            };

            scripts = {
              run-ide.exec = "pycharm-professional > /dev/null 2>&1 &";
              
              led-set.exec = ''
                python src/main.py "$@"
              '';

              format.exec = ''
                isort src/
                black src/
              '';

              lint.exec = ''
                mypy src/
                pylint src/**/*.py
              '';
            };

            processes = {
              main.exec = "python src/main.py";
            };
          };

        };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.
      };
    };
}
