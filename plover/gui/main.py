# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"""The main graphical user interface.

Plover's graphical user interface is a simple task bar icon that pauses and
resumes stenotype translation and allows for application configuration.

"""

import os
import wx
import ConfigParser
import plover.app as app
import plover.config as conf
import plover.gui.config as gui

from plover.exception import InvalidConfigurationError

from plover import __name__ as __software_name__
from plover import __version__
from plover import __copyright__
from plover import __long_description__
from plover import __url__
from plover import __credits__
from plover import __license__


class PloverGUI(wx.App):
    """The main entry point for the Plover application."""

    def __init__(self):
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        """Called just before the application starts."""
        frame = Frame(conf.CONFIG_FILE)
        frame.Show()
        self.SetTopWindow(frame)
        return True


class Frame(wx.Frame):
    """The top-level GUI element of the Plover application."""

    # Class constants.
    TITLE = "Plover alt"
    ALERT_DIALOG_TITLE = TITLE
    ON_IMAGE_FILE = "plover_on.png"
    OFF_IMAGE_FILE = "plover_off.png"
    BORDER = 5
    RUNNING_MESSAGE = "running"
    STOPPED_MESSAGE = "stopped"
    ERROR_MESSAGE = "error"
    CONFIGURE_BUTTON_LABEL = "Configure..."
    ABOUT_BUTTON_LABEL = "About..."
    RAW_BUTTON_LABEL = "Disp RAW"
    COMMAND_SUSPEND = 'SUSPEND'
    COMMAND_RESUME = 'RESUME'
    COMMAND_TOGGLE = 'TOGGLE'
    COMMAND_TOGGLE_RAWDISP = 'TOGGLERAW'
    COMMAND_SHOW_RAWDISP = 'SHOWRAW'
    COMMAND_HIDE_RAWDISP = 'HIDERAW'
    COMMAND_CONFIGURE = 'CONFIGURE'
    COMMAND_FOCUS = 'FOCUS'
    COMMAND_QUIT = 'QUIT'

    def __init__(self, config_file):
        wx.Frame.__init__(self, None,
                          title=Frame.TITLE,
                          pos=wx.DefaultPosition,
                          size=wx.DefaultSize,
                          style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER |
                                                           wx.RESIZE_BOX |
                                                           wx.MAXIMIZE_BOX))
        config_file = config_file
        config = ConfigParser.RawConfigParser()
        config.read(config_file)

        #the raw steno stroke frame, as requested here https://github.com/plover/plover/issues/82
        #The strokelist will contain the strokes and will be passed to the steno engine, so that a listener there can log strokes to it
        self.strokeframe = wx.Frame(None, wx.ID_ANY, title="Raw Plover strokes",pos=wx.DefaultPosition,
                          size=wx.DefaultSize,  style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP) 
        self.strokeframe.Bind(wx.EVT_CLOSE,self._close_raw_frame) #instead of closing, just hide it.
        self.strokelist = wx.ListBox(self.strokeframe,-1)
        
        while True:
            # Check configuration loop
            try:
                self.steno_engine = app.StenoEngine(self.consume_command,self.strokelist)
                break
            except InvalidConfigurationError, spe:
                self.steno_engine = None
                config_dialog = self._create_config_dialog(
                                                    during_plover_init=True)

                alert_dialog = wx.MessageDialog(config_dialog,
                                                unicode(spe),
                                                self.ALERT_DIALOG_TITLE,
                                                wx.OK | wx.ICON_INFORMATION)
                alert_dialog.ShowModal()
                alert_dialog.Destroy()

                ret = config_dialog.ShowModal()
                if ret == wx.ID_CANCEL:
                    self._quit()
                    return

        # Status button.
        on_icon_file = os.path.join(conf.ASSETS_DIR, self.ON_IMAGE_FILE)
        off_icon_file = os.path.join(conf.ASSETS_DIR, self.OFF_IMAGE_FILE)
        self.on_bitmap = wx.Bitmap(on_icon_file, wx.BITMAP_TYPE_PNG)
        self.off_bitmap = wx.Bitmap(off_icon_file, wx.BITMAP_TYPE_PNG)
        self.status_button = wx.BitmapButton(self, bitmap=self.on_bitmap)
        self.status_button.Bind(wx.EVT_BUTTON, self._toggle_steno_engine)

        # Configure button.
        self.configure_button = wx.Button(self,
                                          label=self.CONFIGURE_BUTTON_LABEL)
        self.configure_button.Bind(wx.EVT_BUTTON, self._show_config_dialog)

        # About button.
        self.about_button = wx.Button(self, label=self.ABOUT_BUTTON_LABEL)
        self.about_button.Bind(wx.EVT_BUTTON, self._show_about_dialog)
        
        # Raw button.
        self.raw_button = wx.Button(self, label=self.RAW_BUTTON_LABEL)
        self.raw_button.Bind(wx.EVT_BUTTON, self._show_raw_frame)
        
        # Layout.
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.status_button,
                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.configure_button,
                  flag=wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.about_button,
                  flag=wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
        sizer.Add(self.raw_button,
                  flag=wx.TOP | wx.BOTTOM | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                  border=self.BORDER)
                  
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Bind(wx.EVT_CLOSE, self._quit)
        if self.steno_engine:
            self.steno_engine.add_callback(self._update_status)
        self._update_status()

        # TODO:  auto start the raw steno window when requested in config.

    def consume_command(self, command):
        # Wrap all actions in a CallAfter since the initiator of the
        # action is likely a thread other than the wx thread.
        # TODO: When using keyboard to resume the stroke is typed.
        if command == self.COMMAND_SUSPEND and self.steno_engine:
            wx.CallAfter(self.steno_engine.set_is_running, False)
        elif command == self.COMMAND_RESUME and self.steno_engine:
            wx.CallAfter(self.steno_engine.set_is_running, True)
        elif command == self.COMMAND_TOGGLE and self.steno_engine:
            wx.CallAfter(self.steno_engine.set_is_running,
                         not self.steno_engine.is_running)
        elif command == self.COMMAND_CONFIGURE:
            wx.CallAfter(self._show_config_dialog)
        elif command == self.COMMAND_FOCUS:
            wx.CallAfter(self.Raise)
            wx.CallAfter(self.Iconize, False)
        elif command == self.COMMAND_QUIT:
            wx.CallAfter(self._quit)
        elif command == self.COMMAND_SHOW_RAWDISP:
            wx.CallAfter(self._show_raw_frame)
        elif command == self.COMMAND_HIDE_RAWDISP:
            wx.CallAfter(self._close_raw_frame)

    def _update_status(self):
        if self.steno_engine:
            self.status_button.Enable()
            if self.steno_engine.is_running:
                self.status_button.SetBitmapLabel(self.on_bitmap)
                self.SetTitle("%s: %s" % (self.TITLE, self.RUNNING_MESSAGE))
            else:
                self.status_button.SetBitmapLabel(self.off_bitmap)
                self.SetTitle("%s: %s" % (self.TITLE, self.STOPPED_MESSAGE))
        else:
            self.status_button.Disable()
            self.status_button.SetBitmapLabel(self.off_bitmap)
            self.SetTitle("%s: %s" % (self.TITLE, self.ERROR_MESSAGE))

    def _quit(self, event=None):
        if self.steno_engine:
            self.steno_engine.destroy()
        self.strokeframe.Destroy()
        self.Destroy()

    def _toggle_steno_engine(self, event=None):
        """Called when the status button is clicked."""
        self.steno_engine.set_is_running(not self.steno_engine.is_running)

    def _create_config_dialog(self, event=None, during_plover_init=False):
        """This will create a configuration dialog.

        If during_plover_init is set to True, the user won't be prompted about
        the restart of Plover: his modifications will be used to initialize
        Plover.
        """
        dialog = gui.ConfigurationDialog(conf.CONFIG_FILE,
                                         parent=self,
                                         during_plover_init=during_plover_init)
        return dialog

    def _show_config_dialog(self, event=None):
        dialog = self._create_config_dialog(event)
        dialog.Show()
        return dialog

    def _show_about_dialog(self, event=None):
        """Called when the About... button is clicked."""
        info = wx.AboutDialogInfo()
        info.Name = __software_name__
        info.Version = __version__
        info.Copyright = __copyright__
        info.Description = __long_description__
        info.WebSite = __url__
        info.Developers = __credits__
        info.License = __license__
        wx.AboutBox(info)
        
    def _show_raw_frame(self, event=None):
        self.strokeframe.Show(True) 
        #TODO,  toggle raw
        
    def _close_raw_frame(self, event=None):
        self.strokeframe.Hide()
        

