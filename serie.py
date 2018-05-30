#!/usr/bin/env python
import os
import re
import sys
import stat

class SerieState(object) :
    NONE = 0
    GOT = 1
    SEEN = 2
    GOTSEEN = 3

class ConsoleExporter(object) :
    def out(self, text) :
        sys.stdout.write(text+'\n')

    def err(self, text) :
        sys.stderr.write(text+'\n')

    def debug(self, text) :
        sys.stdout.write(text+'\n')

class SerieOs(object) :
    def listdir(self, dirname) :
        return os.listdir(dirname)
    def filesize(self, filename) :
        return os.lstat(filename).st_size
    def touch(self, filename) :
        #basedir = os.path.basedir(filename)
        #if basedir != '' and not os.exists(basedir) :
        #    os.makedirs(dirname, 0777)
        handle = open(filename,'wb')
        handle.close()
        self.remove_exec(filename)
    def unlink(self, filename) :
        os.unlink(filename)
    def remove_exec(self, filename) :
        S_IX=(stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
        mode = stat.S_IMODE(os.lstat(filename).st_mode)
        if (mode & S_IX != 0) :
            os.chmod(filename, mode &~S_IX)
    def open(self, filename) :
        return open(filename, 'wb')
    def fileexists(self, filename) :
        return os.path.exists(filename)
    def mkdir(self, dirname) :
        if not os.path.exists(dirname) :
            os.makedirs(dirname, 0777)

class Serie(object) :
    SERIE_FILE_RE = re.compile(r'^(\@[\:\_])?([^\[\]\$\!\@\:\~0-9][^\[\]\$\!\@\:\~]*_)?(?:[\[\-\$\!][0-9]+[\]\-\$\!])+(?:[\+\#])?$')
    SERIE_ITEM_RE = re.compile(r'([\[\-\$\!])([0-9]+)[\]\-\$\!]')
    SERIE_FILE_LINK_RE = re.compile(r'^@_([^\[\]\$\!\@\:\~0-9][^\[\]\$\!\@\:\~]*)~(.*)$')
    split_at = 20

    NUM_RE = re.compile(r'^[0-9]+$')
    NUM_RANGE_RE = re.compile(r'^[0-9]+\-[0-9]+$')
    STATE_BEGIN_CHARS = '-[!$'
    STATE_END_CHARS = '-]!$'
    NAMESPACE_WITH_NUM_RE = re.compile(r'^(.*?)([0-9]+)$')

    def __init__(self, serieos, console) :
        self._serieos = serieos
        self._console = console

        self._dir = '.'
        self._namespaces = {}
        self._files = []
        self._write_text = False
        self._write_html = False
        self._new_syntax = True
        self.debug("=> Serie.__init__", None)

    def debug(self, name, value) :
        # print "%s : [%s]" % (name,value)
        # self._console.out("%s : [%s]" % (name,value))
        pass

    def error(self, message) :
        # print message
        self._console.err(message)

    def init_namespace(self, namespace) :
        namespace = namespace.replace(':','_')
        if namespace.endswith('_') :
            raise Exception('No!')
        namespace_num_match = self.NAMESPACE_WITH_NUM_RE.match(namespace)
        if namespace_num_match is not None:
            prefix, count = namespace_num_match.groups()
            namespace = prefix+"%02d" % (int(count),)
        self.debug('namespace',namespace)
        namespace_struct = self._namespaces.setdefault(namespace,{'nums':{},'max':None,'subdir':None})
        return namespace, namespace_struct['nums']

    def set_max(self, namespace, value) :
        self._namespaces[namespace]['max'] = value

    def get_max(self, namespace) :
        return self._namespaces[namespace]['max']

    def set_subdir(self, namespace, value) :
        self._namespaces[namespace]['subdir'] = value

    def get_subdir(self, namespace) :
        if namespace not in self._namespaces :
            return None
        return self._namespaces[namespace]['subdir']

    def get_namespace_by_subdir(self, subdir) :
        for namespace in self.get_namespaces() :
            if self.get_subdir(namespace) == subdir :
                return namespace
        return None

    def scan(self) :
        has_old_syntax = False
        has_new_syntax = False

        subdirs_to_parse = [ None ]
        subdirs_parsed = []

        while len(subdirs_to_parse) > 0 :
            current_subdir = subdirs_to_parse.pop(0)
            if current_subdir not in subdirs_parsed :
                if current_subdir is None :
                    current_dir = '.'
                else :
                    current_dir = current_subdir
                current_namespace = self.get_namespace_by_subdir(current_subdir)

                for filename in self._serieos.listdir(current_dir) :
                    fullfilename = filename
                    if current_subdir is not None :
                        fullfilename = os.path.join(current_dir, filename)
                    size = self._serieos.filesize(fullfilename)
                    if size == 0:
                        self.debug('scanning file', fullfilename)
                        self.debug('current_subdir', current_subdir)
                        self.debug('current_namespace', current_namespace)

                        if (self.SERIE_FILE_RE.match(filename) is not None) :
                            namespace = ''
                            if filename.startswith('@') :
                                has_new_syntax = True
                            else :
                                has_old_syntax = True
                            namespace_parts = filename.split('_')
                            if len(namespace_parts) >= 3 :
                                namespace = '_'.join(namespace_parts[1:-1])
                            if current_namespace is not None :
                                if namespace != '' :
                                    self.debug('namespaces',[current_namespace, namespace])
                                    namespace = '_'.join([current_namespace, namespace])
                                else :
                                    self.debug('namespace alone',current_namespace)
                                    namespace = current_namespace
                            namespace, nums = self.init_namespace(namespace)
                            for state, num in self.SERIE_ITEM_RE.findall(namespace_parts[-1]) :
                                #print state,num
                                state = (self.STATE_BEGIN_CHARS.index(state))
                                num = int(num)
                                # print num,got
                                if num not in nums:
                                    nums[num] = 0
                                nums[num] |= state
                            if filename[-1:] in ('+','#') :
                                self.set_max(namespace, max(nums.keys()))
                                # print "max:",self.get_max(namespace)
                            self._files.append(fullfilename)
                        else :
                            match = self.SERIE_FILE_LINK_RE.match(filename)
                            if match is not None :
                                has_new_syntax = True

                                namespace, subdir = match.groups()
                                subdir = subdir.replace('_', os.sep)
                                if current_subdir is not None :
                                    subdir = os.path.join(current_dir, subdir)
                                if current_namespace is not None :
                                    namespace = '_'.join([current_namespace, namespace])
                                namespace, nums = self.init_namespace(namespace)
                                self.set_subdir(namespace, subdir)
                                if (subdir not in subdirs_to_parse) and (subdir not in subdirs_parsed) :
                                    subdirs_to_parse.append(subdir)
                                    self._serieos.mkdir(subdir)
                                self._files.append(fullfilename)
                subdirs_parsed.append(current_subdir)

        if has_new_syntax :
            self._new_syntax = True
        elif has_old_syntax :
            if any(namespace != '' for namespace in self.get_namespaces()) :
                self._new_syntax = True
            else :
                self._new_syntax = False
        else :
            self._new_syntax = True


    def get_prefix(self, namespace) :
        subdir = self.get_subdir(namespace)
        if self._new_syntax :
            if subdir is not None :
                prefix = os.path.join(subdir, '@_')
            elif namespace == '':
                prefix = '@_'
            else:
                prefix = '@_'+namespace+'_'
        else :
            prefix = ''
        return prefix

    def get_namespaces(self) :
        namespaces = self._namespaces.keys()
        return sorted(namespaces)

    def write_files(self, max_by_namespace):
        files_to_write = []
        files_not_to_remove = []

        for namespace in self.get_namespaces() :
            subdir = self.get_subdir(namespace)
            if subdir is not None :
                if '_' in namespace :
                    parent_namespace, base_namespace = namespace.rsplit('_',1)
                else :
                    parent_namespace = ''
                    base_namespace = namespace
                parent_subdir = self.get_subdir(parent_namespace)
                filename_subdir = subdir
                if parent_subdir is not None :
                    if subdir.startswith(parent_subdir):
                        filename_subdir = subdir[len(parent_subdir):].strip(os.sep)
                filename_subdir = filename_subdir.replace(os.sep,'_')
                filename = self.get_prefix(parent_namespace)
                filename += base_namespace
                filename += '~'
                filename += filename_subdir

                if filename in self._files :
                    files_not_to_remove.append(filename)
                else :
                    files_to_write.append(filename)

            got_all = True
            if max_by_namespace[namespace] is not None :
                digit_count = str(len(str(max_by_namespace[namespace])))
                current_filename = self.get_prefix(namespace)
                all_are_none = True
                for index in xrange(1,max_by_namespace[namespace]+1) :
                    # print "index:",index
                    strnum = ('%0'+digit_count+'d') % (index,)
                    state = self._namespaces[namespace]['nums'].get(index,0)
                    got_all = got_all and ((state & SerieState.GOT) != 0)
                    if state != SerieState.NONE or index == max_by_namespace[namespace] :
                        all_are_none = False
                    current_filename += (self.STATE_BEGIN_CHARS[state]) + strnum + (self.STATE_END_CHARS[state])
                    if index == self.get_max(namespace) :
                        if got_all :
                            current_filename += '#'
                        else :
                            current_filename += '+'
                        all_are_none = False
                    # print current_filename
                    if (index%self.split_at == 0) or (index == max_by_namespace[namespace]) :
                        if not(all_are_none) :
                            if current_filename in self._files :
                                files_not_to_remove.append(current_filename)
                            else :
                                files_to_write.append(current_filename)
                        current_filename = self.get_prefix(namespace)
                        all_are_none = True

        for filename in files_to_write :
            self.debug("create", filename)
            self._serieos.touch(filename)

        for filename in self._files :
            if filename not in files_not_to_remove :
                self.debug("remove", filename)
                self._serieos.unlink(filename)
            else:
                self.debug("keep", filename)
                self._serieos.remove_exec(filename)

    def write_text(self, max_by_namespace) :
        if self._write_text :
            if any(max_by_namespace[namespace] is not None for namespace in self.get_namespaces())  :
                for namespace in self.get_namespaces() :
                    if max_by_namespace[namespace] is not None :
                        got_all = True

                        digit_count = str(len(str(max_by_namespace[namespace])))
                        if namespace != '' :
                            subdir = self.get_subdir(namespace)
                            if subdir is None :
                                self._console.out('%s:' % (namespace,))
                            else :
                                self._console.out('%s (%s):' % (namespace, subdir))
                        line = ''
                        for index in xrange(1,max_by_namespace[namespace]+1) :
                            strnum = ('%0'+digit_count+'d') % (index,)
                            state = self._namespaces[namespace]['nums'].get(index,0)
                            got_all = got_all and ((state & SerieState.GOT) != 0)

                            state_char = ' [!$'[state]
                            state_char_end = state_char.replace('[',']')
                            line += '%s%s%s' % (state_char, strnum, state_char_end)
                            if (index == max_by_namespace[namespace]) or (index % self.split_at == 0) :
                                if index == self.get_max(namespace) :
                                    if got_all :
                                        line += ' ##'
                                    else :
                                        line += ' ++'
                                self._console.out(line)
                                line = ''
                            else :
                                line += ' '
                        self._console.out('')

    def write_html(self, max_by_namespace) :
        if self._write_html or self._serieos.fileexists('serie.html') :
            if any(max_by_namespace[namespace] is not None for namespace in self.get_namespaces())  :
                with self._serieos.open('serie.html') as handle :
                    handle.write('<!doctype html>\n<html>\n<head><style>\nbody { background : #ffffff; }\ntable { border : 1px solid #000000; margin-bottom: 10px; }\ntd { font-family : calibri, sans-serif; font-size : 11px; font-weight : bold; width : 30px; height: 30px; text-align : center; }\n.got { border : 1px solid #000000; }\n.ungot { border : 1px solid #ffffff; }\n.seen { background-color : #f8f; }\n.unseen { }\n.complete { border : 1px solid #000000; }\n.uncomplete { border : 1px dotted #000000; }\n.namespace { font-size : 1.4em; }\n</style>\n</head>\n<body>\n')
                    for namespace in self.get_namespaces() :
                        if max_by_namespace[namespace] is not None :
                            digit_count = str(len(str(max_by_namespace[namespace])))
                            handle.write('<table class="%s">\n' % ('complete' if self.get_max(namespace) is not None else 'uncomplete'))
                            if namespace != '' :
                                handle.write('<tr><td class="namespace" colspan="20">%s</td></tr>\n' % (namespace))
                            for index in xrange(1,max_by_namespace[namespace]+1) :
                                if (index % self.split_at == 1) :
                                    handle.write('<tr>')
                                strnum = ('%0'+digit_count+'d') % (index,)
                                state = self._namespaces[namespace]['nums'].get(index,0)
                                # got_all = got_all and ((state & SerieState.GOT) != 0)
                                handle.write('<td class="%s %s">%s</td>' % ('got' if state & SerieState.GOT else 'ungot','seen' if state & SerieState.SEEN else 'unseen',strnum))
                                if (index == max_by_namespace[namespace]) or (index % self.split_at == 0) :
                                    handle.write('</tr>\n')
                            handle.write('</table>\n')
                    handle.write('</body>\n</html>\n')
            else :
                self._serieos.unlink('serie.html')

    def write(self) :
        max_by_namespace = {}
        for namespace in self.get_namespaces() :
            max_by_namespace[namespace] = self.get_max(namespace)
            if max_by_namespace[namespace] is None :
                if len(self._namespaces[namespace]['nums']) > 0 :
                    max_by_namespace[namespace] = max(self._namespaces[namespace]['nums'].keys())
                else :
                    pass
        self.write_files(max_by_namespace)
        self.write_html(max_by_namespace)
        self.write_text(max_by_namespace)

    def main(self, *argv) :
        self.scan()
        self.add_items(*argv)
        self.write()

    def add_items(self,*argv) :
        for item in argv :
            self.add_item(item)

    def add_item(self, item) :
        self.debug('item',item)
        if item == 'html' :
            self._write_html = True
        elif item == 'text' :
            self._write_text = True
        elif item in ('m','migration') :
            self._new_syntax = True
        elif item in ('f','flatten') :
            self.flatten()
        elif '~' in item :
            namespace, rawitem = item.split('~',1)
            self.add_link(namespace, rawitem)
        elif ':' in item :
            namespace, rawitem = item.rsplit(':',1)
            self.add_num_item(namespace, rawitem)
        elif '_' in item :
            namespace, rawitem = item.rsplit('_',1)
            self.add_num_item(namespace, rawitem)
        else :
            self.add_num_item('', item)

    def add_link(self, namespace, item) :
        namespace, nums = self.init_namespace(namespace)
        if item is not None and item != '' :
            item = item.replace('_',os.sep)
            item = item.strip(os.sep)
            self.set_subdir(namespace, item)
            self._serieos.mkdir(item)

    def add_num_item(self, namespace, item) :
        namespace, nums = self.init_namespace(namespace)
        if item[:1] == 'e' :
            item = item[1:]
            if item == '' :
                self.set_max(namespace, max(nums.keys()))
            else :
                self.set_max(namespace, int(item))
        else :
            states_infos = {
                '+' : (SerieState.GOT, True),
                '-' : (SerieState.GOT, False),
                's' : (SerieState.SEEN, True),
                'u' : (SerieState.SEEN, False),
                }
            states = []
            while item[:1] in states_infos.keys() :
                states.append(states_infos[item[:1]])
                item = item[1:]
            if len(states) == 0 :
                states.append(states_infos['+'])
            item_nums = []
            for element in item.split(",") :
                match = self.NUM_RE.match(element)
                if match is not None :
                    item_nums.append(int(element))
                else :
                    match = self.NUM_RANGE_RE.match(element)
                    if match is not None :
                        start,end = map(int,element.split('-',2))
                        if end<start :
                            start,end = end,start
                        item_nums = item_nums + list(xrange(start,end+1))
                    else :
                        self.error("Can't understand [%s]" % element)
            for num in item_nums :
                for state_change, state_change_add in states :
                    if state_change_add :
                        nums[num] = nums.get(num,SerieState.NONE) | state_change
                    else :
                        nums[num] = nums.get(num,SerieState.NONE) & ~state_change

    def flatten(self) :
        for namespace in self.get_namespaces() :
            self._namespaces[namespace]['subdir'] = None

if __name__ == '__main__' :
    serieos = SerieOs()
    console_exporter = ConsoleExporter()
    Serie(serieos, console_exporter).main(*(sys.argv[1:]))

