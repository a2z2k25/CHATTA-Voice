{
  description = "Voice Mode - Natural voice conversations for AI assistants";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          virtualenv
        ]);
        
        # Wrapper script that uses uvx with proper environment
        voice-mode = pkgs.writeShellScriptBin "voice-mode" ''
          export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
            pkgs.portaudio
            pkgs.libpulseaudio
            pkgs.alsa-lib
            pkgs.stdenv.cc.cc.lib
          ]}:$LD_LIBRARY_PATH"
          
          # Add build-time dependencies for compilation
          export PKG_CONFIG_PATH="${pkgs.lib.makeSearchPathOutput "dev" "lib/pkgconfig" [
            pkgs.alsa-lib
            pkgs.portaudio
            pkgs.libpulseaudio
          ]}:$PKG_CONFIG_PATH"
          
          # Add development headers to C include path
          export CPATH="${pkgs.lib.makeSearchPathOutput "dev" "include" [
            pkgs.alsa-lib
            pkgs.portaudio
            pkgs.libpulseaudio
          ]}:$CPATH"
          
          # Add library paths for linking
          export LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
            pkgs.alsa-lib
            pkgs.portaudio
            pkgs.libpulseaudio
          ]}:$LIBRARY_PATH"
          
          # Make sure gcc, pkg-config, and ffmpeg are available
          export PATH="${pkgs.gcc}/bin:${pkgs.pkg-config}/bin:${pkgs.ffmpeg}/bin:$PATH"
          
          exec ${pkgs.uv}/bin/uvx voice-mode "$@"
        '';
      in
      {
        packages.default = voice-mode;
        
        devShells.default = pkgs.mkShell {
          # Build-time dependencies (available during build)
          nativeBuildInputs = with pkgs; [
            pkg-config
            gcc
          ] ++ pkgs.lib.optionals pkgs.stdenv.isLinux [
            alsa-lib.dev  # ALSA headers for building simpleaudio
            libpulseaudio.dev # PulseAudio headers
          ];
          
          # Runtime dependencies
          buildInputs = with pkgs; [
            # Python
            pythonEnv
            uv
            
            # Audio libraries (runtime)
            portaudio
            libpulseaudio
            alsa-lib
            ffmpeg
            
            # Audio tools
            pulseaudio
            alsa-utils
            
            # Additional tools
            git
          ];
          
          shellHook = ''
            echo "Voice Mode NixOS development environment"
            echo "Python ${pkgs.python312.version} with uv and audio dependencies"
            
            # Set up library paths
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.portaudio
              pkgs.libpulseaudio
              pkgs.alsa-lib
              pkgs.stdenv.cc.cc.lib
            ]}:$LD_LIBRARY_PATH"
            
            # Set up pkg-config for build-time compilation
            export PKG_CONFIG_PATH="${pkgs.alsa-lib.dev}/lib/pkgconfig:${pkgs.portaudio}/lib/pkgconfig:${pkgs.libpulseaudio.dev}/lib/pkgconfig:$PKG_CONFIG_PATH"
            
            # Add development headers to C include path
            export CPATH="${pkgs.alsa-lib.dev}/include:${pkgs.portaudio}/include:${pkgs.libpulseaudio.dev}/include:$CPATH"
            
            # Add library paths for linking
            export LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
              pkgs.alsa-lib
              pkgs.portaudio
              pkgs.libpulseaudio
            ]}:$LIBRARY_PATH"
            
            # Create venv if it doesn't exist
            if [ ! -d .venv ]; then
              echo "Creating virtual environment..."
              uv venv
            fi
            
            echo ""
            echo "To activate the virtual environment, run: source .venv/bin/activate"
            echo "Then install voice-mode with: uv pip install -e ."
            echo "Or run directly with: uvx voice-mode"
          '';
        };
      });
}
