{
  description = "My PC RGB";

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
        let
          defaultPackages = with pkgs; [
            python313
            libusb1
            hidapi
          ];
          python = pkgs.python313;
        in
        {
          devenv.shells.default = {
            name = "my-pc-rgb";

            packages = defaultPackages ++ (with pkgs; [ i2c-tools ]);

            languages.python = {
              enable = true;
              package = python;
              venv.enable = true;
              venv.requirements = ''
                pyusb>=1.3.1
                hid>=1.0.8
                smbus3>=0.5.5

                black>=25.9.0
                isort>=6.0.1
                mypy>=1.18.2
                pylint>=3.3.8
              '';
            };

            scripts = {
              run-ide.exec = "pycharm-professional > /dev/null 2>&1 &";

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

          packages.default = python.pkgs.buildPythonApplication {
            pname = "my-pc-rgb";
            version = "0.1.0";
            pyproject = false;

            src = ./.;

            nativeBuildInputs = [ pkgs.makeWrapper ];

            propagatedBuildInputs =
              defaultPackages
              ++ (with python.pkgs; [
                pyusb
                hid
              ])
              ++ [
                (python.pkgs.buildPythonPackage rec {
                  pname = "smbus3";
                  version = "0.5.5";
                  pyproject = true;

                  build-system = with python.pkgs; [
                    setuptools
                  ];

                  src = pkgs.fetchPypi {
                    inherit pname version;
                    hash = "sha256-ke7Tj7a30viT+/w/NwBqpB5pE/3aWzqaeSOLNTdg+S4=";
                  };
                  doCheck = false;
                })
              ];

            installPhase = ''
              mkdir -p $out/share/my-pc-rgb
              cp -r src/* $out/share/my-pc-rgb/
            '';

            postFixup = ''
              makeWrapper ${python}/bin/python $out/bin/my-pc-rgb \
                --add-flags "$out/share/my-pc-rgb/main.py" \
                --prefix PYTHONPATH : "$out/share/my-pc-rgb:$PYTHONPATH"
            '';
          };

        };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.
      };
    };
}
