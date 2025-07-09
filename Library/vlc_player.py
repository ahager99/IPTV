import os
import sys
import vlc
import logging

# Add the directory containing libvlc.dll to the PATH
script_dir = os.path.dirname(os.path.abspath(__file__)) + "\\Library\\"
os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")


class VLCPlayer:
    
    media_path = None
    player = None
    instance = None

    def __init__(self, media_path=None, silent=True):
        
        self.media_path = media_path


        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        
        if silent:
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
        else:
            self.instance = vlc.Instance(
                [
                    f"--config={base_path}\\include\\vlcrc",
                    "--vout=directx",
                    "--no-plugins-cache",
                    "--log-verbose=1",
                ]
            )
        
        self.player = self.instance.media_player_new()
        if media_path:
            self.set_media(media_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Release old instances safely
        if self.player:
            self.player.release()
        if self.instance:
            self.instance.release()

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

    