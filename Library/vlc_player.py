import os
import sys
import vlc
import logging

# Add the directory containing libvlc.dll to the PATH
script_dir = os.path.dirname(os.path.abspath(__file__)) + "\\Library\\"
os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")


class VLCPlayer:
    
    def __init__(self, media_path=None):
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        
        self.instance = vlc.Instance(
            [
                f"--config={base_path}\\include\\vlcrc",
                "--repeat",
                "--no-xlib",
                "--no-audio",
                "--vout=directx",
                "--no-plugins-cache",
                "--log-verbose=0",
                "--quiet",
                #"--no-verbose",
                "--logmode=none",
            ]
        )
        
        self.player = self.instance.media_player_new()
        if media_path:
            self.set_media(media_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.player.release()

    def set_media(self, media_path):
        media = self.instance.media_new(media_path)
        self.player.set_media(media)

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def is_playing(self):
        return self.player.is_playing()

    def set_volume(self, volume):
        self.player.audio_set_volume(volume)

    def get_volume(self):
        return self.player.audio_get_volume()

    def get_time(self):
        return self.player.get_time()

    def set_time(self, ms):
        self.player.set_time(ms)

    def get_length(self):
        return self.player.get_length()
    
    # check if playback failed
    def playback_failed(self): 
        if self.player.get_state() == vlc.State.Error:
            logging.debug("Playback failed: VLC encountered an error.")
            return True
        elif self.player.get_state() == vlc.State.Ended:
            logging.debug("Playback ended unexpected.")
            return True
        return False

    def restart_vlc_instance(self):
        referer_url = (
            self.hostname_input.text()
        )  # Get the referer URL from the hostname
        base_path = (
            sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath(".")
        )
        proxy_address = self.proxy_input.text()

        # Modify VLC proxy settings
        self.modify_vlc_proxy(proxy_address)

        # Release old instances safely
        if self.videoPlayer:
            self.videoPlayer.release()
        if self.instance:
            self.instance.release()

        # Validate config path
        config_path = f"{base_path}\\include\\vlcrc"
        if not os.path.exists(config_path):
            logging.error(f"VLC config file not found: {config_path}")
            return

        # Initialize VLC
        try:
            logging.debug("Initializing VLC instance.")
            self.instance = vlc.Instance(
                [
                    f"--config={config_path}",
                    f"--http-proxy={proxy_address}",
                    f"--http-referrer={referer_url}",
                    "--repeat",
                    "--no-xlib",
                    "--vout=directx",
                    "--no-plugins-cache",
                    "--log-verbose=1",
                    "--network-caching=1000",
                    "--live-caching=1000",
                    "--file-caching=3000",
                    "--live-caching=3000",
                    "--sout-mux-caching=2000",
                ]
            )

            if not self.instance:
                raise Exception("Failed to initialize VLC instance.")

            self.videoPlayer = self.instance.media_player_new()
            if not self.videoPlayer:
                raise Exception("Failed to create VLC media player.")

            if sys.platform.startswith("linux"):
                self.videoPlayer.set_xwindow(self.video_frame.winId())
            elif sys.platform == "win32":
                self.videoPlayer.set_hwnd(self.video_frame.winId())
            elif sys.platform == "darwin":
                self.videoPlayer.set_nsobject(int(self.video_frame.winId()))

            # Disable mouse and key input
            self.videoPlayer.video_set_mouse_input(False)
            self.videoPlayer.video_set_key_input(False)

        except Exception as e:
            logging.error(f"Error during VLC instance restart: {e}")