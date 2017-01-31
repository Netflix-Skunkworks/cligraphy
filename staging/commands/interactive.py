import logging


def ipython():
    from IPython.terminal.ipapp import TerminalIPythonApp
    app = TerminalIPythonApp.instance()
    app.initialize(argv=[]) # argv=[] instructs IPython to ignore sys.argv
    app.start()


def main():
    try:
        ipython()
    except ImportError:
        logging.warning('ipython not available, using built-in console')
        import code
        code.interact(local=locals())
