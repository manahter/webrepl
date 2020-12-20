from time import gmtime, strftime
import os

__author__    = 'Manahter'
__copyright__ = 'Copyright 2020, Noter'
__version__   = '1.0.8'
__date__      = "16.12.2020"

dirname = os.path.dirname(__file__)
path_mode = "{}/mode".format(dirname)
path_keep = "{}/keep".format(dirname)
_modes_ = {
    "iNFO": 1,  # Grey
    "INFO": 2,
    "WARNING": 3,
    "NOTICE": 4,
    "ERROR": 5
}

# Eski dosya varsa silinir.
if "keep" in os.listdir(dirname):
    os.remove(path_keep)


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    ITALIC = '\33[3m'
    URL = '\33[4m'
    BLINK = '\33[5m'
    BLINK2 = '\33[6m'
    SELECTED = '\33[7m'

    BLACK = '\33[30m'
    RED = '\33[31m'
    GREEN = '\33[32m'
    YELLOW = '\33[33m'
    BLUE = '\33[34m'
    VIOLET = '\33[35m'
    BEIGE = '\33[36m'
    WHITE = '\33[37m'

    BLACKBG = '\33[40m'
    REDBG = '\33[41m'
    GREENBG = '\33[42m'
    YELLOWBG = '\33[43m'
    BLUEBG = '\33[44m'
    VIOLETBG = '\33[45m'
    BEIGEBG = '\33[46m'
    WHITEBG = '\33[47m'

    GREY = '\33[90m'
    RED2 = '\33[91m'
    GREEN2 = '\33[92m'
    YELLOW2 = '\33[93m'
    BLUE2 = '\33[94m'
    VIOLET2 = '\33[95m'
    BEIGE2 = '\33[96m'
    WHITE2 = '\33[97m'

    GREYBG = '\33[100m'
    REDBG2 = '\33[101m'
    GREENBG2 = '\33[102m'
    YELLOWBG2 = '\33[103m'
    BLUEBG2 = '\33[104m'
    VIOLETBG2 = '\33[105m'
    BEIGEBG2 = '\33[106m'
    WHITEBG2 = '\33[107m'


class Noter:
    """
    :func common: type, module, messager, message, color
        :param type: str: "INFO", "WARNING", "ERROR", "NOTICE".. anything
        :param module: str: "Self module Name" ... anything
        :param messager: str: "Func name" ... anything
        :param message: str: "I done" ... anything

        [ type ] [ module ] messager: message
    Example 1:
        # Create
        noter = Noter(module="Scaner")

        # or Call1
        noter.info("scan_start", "Scanning started...")
        >> [ INFO ] [ Scaner ] scan_start: Scanning started...

        # Call 2
        noter.info( messager="scan_start", message="Scanning started...")
        >> [ INFO ] [ Scaner ] scan_start: Scanning started...


    Example 2:
        # Direct Call-1 without create
        Noter.info("scan_start", "Scanning started...")
        >> [ INFO ] scan_start: Scanning started...

        # Direct Call-2 without create
        Noter.info(module="Scaner", messager="scan_start", message="Scanning started...")
        >> [ INFO ] [ Scaner ] scan_start: Scanning started...

    """
    """Want do you keep?"""
    _keep = False
    _mode = 0
    module = ""
    messager = ""

    def __init__(self, module="", module_path="", messager="", mode=-1, keep=False):
        self.messager = messager
        self.module = module
        self.mode = mode
        self._keep = keep

        if module_path:
            self.notice("Loaded", module_path)

    @property
    def mode(self):
        """
        Flag
            0 -> Don't print
            1 -> print : info, info_grey, warning, error, notice
            2 -> print : info, warning, error, notice
            3 -> print : warning, error, notice
            4 -> print : warning, error
            5 -> print : error
        :return:
        """
        if not os.path.exists(path_mode):
            return 0
        with open(path_mode) as f:
            data = f.read().strip()
            return int(data) if data.isdigit() else 0


    @mode.setter
    def mode(self, val):
        """Set only self"""
        if type(val) != int or (type(val) == int and val < 0):
            return

        with open(path_mode, "w") as f:
            if type(val) == int:
                f.write(str(val))

        self._mode = val

    @property
    def keep(self):
        return self._keep

    @keep.setter
    def keep(self, val):
        if type(val) == str and self._keep:
            with open(path_keep, "a") as f:
                f.write(val.replace("\n", "") + "\n")

    def info(*args, **kwargs):
        Noter.common(*args, type="INFO", color=Color.GREEN, **kwargs)

    def info_grey(*args, **kwargs):
        Noter.common(*args, type="iNFO", color=Color.GREY, **kwargs)

    def warning(*args, **kwargs):
        Noter.common(*args, type="WARNING", color=Color.YELLOW, **kwargs) # NOTICE

    def error(*args, **kwargs):
        Noter.common(*args, type="ERROR", color=Color.RED, **kwargs)

    def notice(*args, **kwargs):
        Noter.common(*args, type="NOTICE", color=Color.BLUE, **kwargs)

    def common(*args, **kwargs):
        args = list(args)
        self = args.pop(0) if len(args) and type(args[0]) == Noter else Noter

        tipi = kwargs.get("type", "NOT")
        mode = self.mode
        if not mode or _modes_.get(tipi, 1) < mode:
            return

        module = kwargs.get("module", self.module)
        messager = kwargs.get("messager", self.messager or (args[0] if len(args) else ""))
        message = kwargs.get("message", (args[1] if len(args) > 1 else ""))

        pres = ["[{}{}{: ^7s}{}]".format(Color.BOLD, kwargs.get("color", Color.GREY), tipi, Color.END)]

        if module:
            pres.append("{:10}>".format(module))

        if messager:
            pres.append("{:12}".format(messager))

        if message:
            pres.append(": " + message)

        print(*pres)

        if self.keep:
            pres[0] = "|{: ^7s}|".format(tipi)
            pres.insert(0, strftime("%Y-%m-%d %H:%M:%S", gmtime()))
            self.keep = " ".join(pres)
