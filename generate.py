import re
import os
import shutil
import yaml
import datetime

# TEMPLITE : http://code.activestate.com/recipes/496702/
class Template():
    def __init__(self, text):
        self.delimiter = re.compile(r'{%(.*?)%}', re.DOTALL)
        self.tokens = self.compile(text)

    def compile(self, text):
        tokens = []
        for index, token in enumerate(self.delimiter.split(text)):
            if index % 2 == 0:
                # plain string
                if token:
                    tokens.append((False, token.replace('%\}', '%}').replace('{\%', '{%')))
            else:
                # code block
                # find out the indentation
                lines = token.replace('{\%', '{%').replace('%\}', '%}').splitlines()
                indent = min([len(l) - len(l.lstrip()) for l in lines if l.strip()])
                realigned = '\n'.join(l[indent:] for l in lines)
                tokens.append((True, compile(realigned, '<tempalte> %s' % realigned[:20], 'exec')))
        return tokens

    def tex_escape(self, text):
        """
            :param text: a plain text message
            :return: the message escaped to appear correctly in LaTeX
        """
        text = str(text)
        conv = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
            '\\': r'\textbackslash{}',
            '<': r'\textless ',
            '>': r'\textgreater ',
        }
        regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
        return regex.sub(lambda match: conv[match.group()], text)

    def to_date(self, text):
        date = datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S%z")
        return date.strftime("%b. %Y")

    def to_specific_date(self, text):
        date = datetime.datetime.strptime(str(text), "%Y-%m-%d %H:%M:%S%z")
        return date.strftime("%b. %d, %Y")

    def render(self, context = None, **kw):
        """Render the template according to the given context"""
        global_context = {}
        if context: global_context.update(context)
        if kw: global_context.update(kw)

        # add function for output
        def emit(*args):
            result.extend([self.tex_escape(arg) for arg in args])
        def emit_tex(*args):
            result.extend([str(arg) for arg in args])
        def emit_braces(*args):
            result.extend(["{"+self.tex_escape(arg)+"}" for arg in args])
        def to_date(arg):
             return self.to_date(arg)
        def to_specific_date(arg):
             return self.to_specific_date(arg)
        def fmt_emit(fmt, *args):
            result.append(fmt % args)
        def list_to_string(arg):
            return " and ".join([", ".join(arg[:-1]),arg[-1]] if len(arg) > 2 else arg)

        global_context['emit'] = emit
        global_context['fmt_emit'] = fmt_emit
        global_context['emit_braces'] = emit_braces
        global_context['emit_tex'] = emit_tex
        global_context['to_date'] = to_date
        global_context['to_specific_date'] = to_specific_date
        global_context['list_to_string'] = list_to_string

        # run the code
        result = []
        for is_code, token in self.tokens:
            if is_code: exec(token, global_context)
            else: result.append(token)
        return ''.join(result)

class Generate:
    def __init__(self, src, dst, data_src, extension, main, latex):
        self.src = src
        self.dst = dst
        self.data_src = data_src
        self.extension = extension
        self.main = main
        self.latex = latex

    def parseTemplate(self, filename):
        template = open(filename).read()
        output = Template(template).render(self.context)
        output_file = filename.replace(self.src, self.dst).replace(self.extension, "")
        self.mkdir(output_file)
        with open(output_file, "w") as text_file: text_file.write(output)

    def computeContext(self):
        self.context = {}
        for root, directories, filenames in os.walk(self.data_src):
            for filename in filenames:
                path = os.path.join(root, filename)
                stram = open(path, "r")
                content = yaml.load(stram)
                key = os.path.splitext(filename)[0]
                self.context[key] = content

    def retrieveTemplates(self):
        for root, directories, filenames in os.walk(self.src):
            for filename in filenames:
                if filename.endswith(self.extension):
                    path = os.path.join(root, filename)
                    self.parseTemplate(path)

    def mkdir(self, path):
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.makedirs(os.path.dirname(path))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def copyFile(self, src, dest):
        try:
            shutil.copy(src, dest)
        # eg. src and dest are the same file
        except shutil.Error as e:
            print('Error: %s' % e)
        # eg. source or destination doesn't exist
        except IOError as e:
            print('Error: %s' % e.strerror)

    # copy fixed files from src to dst
    def copyFiles(self):
        try:
            shutil.rmtree(self.dst)
        except IOError as e:
            pass
        for root, directories, filenames in os.walk(self.src):
            for filename in filenames:
                if not filename.endswith(self.extension):
                    orig = os.path.join(root,filename)
                    new = orig.replace(self.src, self.dst)
                    self.mkdir(new)
                    self.copyFile(orig, new)

    def compileLatex(self):
        savedPath = os.getcwd()
        os.chdir(self.dst)
        os.system(self.latex + " -output-directory=" + savedPath + " " + self.main + "")
        os.chdir(savedPath)
        os.remove(self.main.replace('tex', 'aux'))
        os.remove(self.main.replace('tex', 'log'))
        os.remove(self.main.replace('tex', 'out'))

    def run(self):
        self.copyFiles()
        self.computeContext()
        self.retrieveTemplates()
        self.compileLatex()

# main function
def main():
    # information about output location for the tex files
    dst = "./dst/"
    # information about the location for the template files
    src = "./src/"
    # information about the location for the data files
    data_src = "../../projects/theaxec.github.io/_data/"
    # extension used for templates
    extension = ".template"
    # main file
    main_file = "cv.tex"
    # latex command
    latex = "xelatex"
    # create and run the engine
    engine = Generate(src, dst, data_src, extension, main_file, latex)
    engine.run()

# entry point
if __name__ == "__main__":
    main()
