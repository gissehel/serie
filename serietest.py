#!/usr/bin/env python

import os
import sys
import unittest
from serie import Serie

class ConsoleExporterMock(object) :
    def __init__(self) :
        self._outs = []
        self._errs = []

    def errs(self) :
        return self._errs

    def outs(self) :
        return self._outs

    def out(self, text) :
        # sys.stdout.write(text+'\n')
        self._outs.append(text)

    def err(self, text) :
        sys.stderr.write(text+'\n')
        self._errs.append(text)

    def debug(self, text) :
        self.stdout.write(text+'\n')

    def clear_out(self) :
        self._outs.clear()

class DirMock(object) :
    def __init__(self, dirname) :
        self._dirname = dirname
        self._z = set()
        self._nz = set()
        class FileClass(object) :
            def __init__(self, filename, z, nz) :
                self._buffer = ''
                self._z = z
                self._nz = nz
                self._filename = filename
            def __enter__(self):
                self._buffer = ''
            def write(self, data) :
                self._buffer += data
            def __exit__(self, *args, **kwargs) :
                if len(self._buffer) == 0 :
                    self._z.add(self._filename)
                else :
                    self._nz.add(self._filename)
        self._fileclass = FileClass
    def listdir(self,dirname) :
        # print "dirname: [%s][%s]" % (self._dirname, dirname)
        return sorted(list(self._z) + list(self._nz))
    def filesize(self, filename) :
        if filename in self._z :
            return 0
        if filename in self._nz :
            return 1
        raise IOError()
    def touch(self, filename) :
        if (filename not in self._z) and (filename not in self._nz) :
            self._z.add(filename)
    def unlink(self, filename) :
        if filename in self._z :
            self._z.remove(filename)
        elif filename in self._nz :
            self._nz.remove(filename)
        else :
            raise IOError()
    def remove_exec(self, filename):
        pass
    def open(self, filename) :
        return self._fileclass(filename, self._z, self._nz)
    def fileexists(self, filename) : 
        return (filename in self._z) or (filename in self._nz)
    def mkdir(self, dirname) :
        pass
    def apply(self, method_name, filename):
        # print "apply: [%s][%s][%s]" % (self._dirname, method_name, filename)
        method = getattr(self, method_name)
        return method(filename)

class SerieOsMock(object) :
    def __init__(self) :
        self._dirs = {}
    def _get_dirmock_filename(self, global_filename) :
        basename = os.path.basename(global_filename)
        dirname = os.path.dirname(global_filename)
        if dirname == '.' :
            dirname = ''
        if dirname not in self._dirs :
            self._dirs[dirname] = DirMock(dirname)
        return self._dirs[dirname], basename
    def apply(self, method_name, filename):
        dirmock, basename = self._get_dirmock_filename(filename)
        return dirmock.apply(method_name, basename)
    def listdir(self,dirname) :
        return self.apply('listdir', os.path.join(dirname, '.'))
    def filesize(self, filename) :
        return self.apply('filesize', filename)
    def touch(self, filename) :
        return self.apply('touch', filename)
    def unlink(self, filename) :
        return self.apply('unlink', filename)
    def remove_exec(self, filename):
        return self.apply('remove_exec', filename)
    def open(self, filename) :
        return self.apply('open', filename)
    def fileexists(self, filename) :
        return self.apply('fileexists', filename)
    def mkdir(self, dirname) :
        return self.apply('mkdir', dirname)

class TestSerie(unittest.TestCase) :
    def setUp(self) :
        self.maxDiff = None
        self._serieos = SerieOsMock()
        self._console = ConsoleExporterMock()

    def tearDown(self) :
        self.assertEqual(self._console.errs(),[])

    def assert_files(self, filenames, subdir=None) :
        if subdir is None :
            listdir = self._serieos.listdir('.')
        else :
            listdir = self._serieos.listdir(subdir)
        self.assertEqual(sorted(listdir),sorted(filenames))

    def assert_out(self, lines) :
        self.assertEqual(self._console.outs(), lines)

    def main(self,*args,**kwargs) :
        self._serie = Serie(self._serieos, self._console)
        self._serie.main(*args,**kwargs)

    def touch(self,filenames) :
        for filename in filenames :
            self._serieos.touch(filename)

    def test_old_basic(self) :
        self.touch(['-1-'])
        self.main('7')
        self.assert_files(['-1--2--3--4--5--6-[7]'])
    def test_old_end(self) :
        self.touch(['-1-'])
        self.main('7')
        self.main('e9')
        self.assert_files(['-1--2--3--4--5--6-[7]-8--9-+'])
    def test_old_size_0_00(self) :
        self.touch(['-1-'])
        self.main('7')
        self.assert_files(['-1--2--3--4--5--6-[7]'])
        self.main('11')
        self.assert_files(['-01--02--03--04--05--06-[07]-08--09--10-[11]'])
    def test_old_size_sep_20(self) :
        self.touch(['-1-'])
        self.main('7')
        self.assert_files(['-1--2--3--4--5--6-[7]'])
        self.main('11')
        self.assert_files(['-01--02--03--04--05--06-[07]-08--09--10-[11]'])
        self.main('31')
        self.assert_files(['-01--02--03--04--05--06-[07]-08--09--10-[11]-12--13--14--15--16--17--18--19--20-','-21--22--23--24--25--26--27--28--29--30-[31]'],)
    def test_old_empty_row(self) :
        self.touch(['-1-'])
        self.main('7','51')
        self.assert_files(['-01--02--03--04--05--06-[07]-08--09--10--11--12--13--14--15--16--17--18--19--20-','-41--42--43--44--45--46--47--48--49--50-[51]'],)

    def test_new_basic(self) :
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])
    def test_new_end(self) :
        self.main('7')
        self.main('e9')
        self.assert_files(['@_-1--2--3--4--5--6-[7]-8--9-+'])
    def test_new_size_0_00(self) :
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])
        self.main('11')
        self.assert_files(['@_-01--02--03--04--05--06-[07]-08--09--10-[11]'])
    def test_new_size_sep_20(self) :
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])
        self.main('11')
        self.assert_files(['@_-01--02--03--04--05--06-[07]-08--09--10-[11]'])
        self.main('31')
        self.assert_files(['@_-01--02--03--04--05--06-[07]-08--09--10-[11]-12--13--14--15--16--17--18--19--20-','@_-21--22--23--24--25--26--27--28--29--30-[31]'],)
    def test_new_empty_row(self) :
        self.main('7','51')
        self.assert_files(['@_-01--02--03--04--05--06-[07]-08--09--10--11--12--13--14--15--16--17--18--19--20-','@_-41--42--43--44--45--46--47--48--49--50-[51]'],)

    def test_newsyntax_migration(self):
        self.touch(['-1-'])
        self.main('7')
        self.assert_files(['-1--2--3--4--5--6-[7]'])
        self.main('m')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])

    def test_newsyntax_migration_2(self):
        self.touch(['-1-'])
        self.main('7')
        self.assert_files(['-1--2--3--4--5--6-[7]'])
        self.main('migration')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])

    def test_namespace_basic(self):
        self.main('name:7')
        self.assert_files(['@_name_-1--2--3--4--5--6-[7]'])

    def test_namespace_numeral(self):
        self.main('name3:7')
        self.assert_files(['@_name03_-1--2--3--4--5--6-[7]'])

    def test_mix_namespaces(self):
        self.main('name3:7','name001:5')
        self.assert_files(['@_name01_-1--2--3--4-[5]','@_name03_-1--2--3--4--5--6-[7]'])
        self.main('name3:2-4','name1:s3-6','23')
        self.assert_files(['@_-21--22-[23]','@_name01_-1--2-!3!!4!$5$!6!','@_name03_-1-[2][3][4]-5--6-[7]'])

    def test_mix_namespaces_with_comma(self):
        self.main('name3:7','name001:5')
        self.assert_files(['@_name01_-1--2--3--4-[5]','@_name03_-1--2--3--4--5--6-[7]'])
        self.main('name3:2,4','name1:s3,6','23')
        self.assert_files(['@_-21--22-[23]','@_name01_-1--2-!3!-4-[5]!6!','@_name03_-1-[2]-3-[4]-5--6-[7]'])

    def test_end2(self) :
        self.main('7')
        self.main('-9')
        self.assert_files(['@_-1--2--3--4--5--6-[7]-8--9-'])
    def test_interval_creation(self) :
        self.main('3-7')
        self.assert_files(['@_-1--2-[3][4][5][6][7]'])
    def test_interval_use(self) :
        self.main('9')
        self.assert_files(['@_-1--2--3--4--5--6--7--8-[9]'])
        self.main('3-7')
        self.assert_files(['@_-1--2-[3][4][5][6][7]-8-[9]'])
    def test_interval_overlap(self) :
        self.main('9')
        self.assert_files(['@_-1--2--3--4--5--6--7--8-[9]'])
        self.main('2-5','4-7')
        self.assert_files(['@_-1-[2][3][4][5][6][7]-8-[9]'])
    def test_consolidate(self) :
        self.touch(['[7]'])
        self.assert_files(['[7]'])
        self.main()
        self.assert_files(['-1--2--3--4--5--6-[7]'])
    def test_consolidate_multiple(self) :
        self.touch(['[7]','[14][9]'])
        self.assert_files(['[7]','[14][9]'])
        self.main()
        self.assert_files(['-01--02--03--04--05--06-[07]-08-[09]-10--11--12--13-[14]'])
    def test_consolidate_multiple_overlap(self) :
        self.touch(['[7][8][9]','[08][09][10][11]'])
        self.main()
        self.assert_files(['-01--02--03--04--05--06-[07][08][09][10][11]'])
    def test_consolidate_multiple_overlap_oldandnewsyntax(self) :
        self.touch(['[7][8][9]','@_[08][09][10][11]'])
        self.main()
        self.assert_files(['@_-01--02--03--04--05--06-[07][08][09][10][11]'])
    def test_suppression_basic(self) :
        self.main('9')
        self.assert_files(['@_-1--2--3--4--5--6--7--8-[9]'])
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]-8-[9]'])
        self.main('-7')
        self.assert_files(['@_-1--2--3--4--5--6--7--8-[9]'])
    def test_suppression_end_empty(self) :
        self.main('e7','-7')
        self.assert_files(['@_-1--2--3--4--5--6--7-+'])
    def test_seen_basic(self) :
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])
        self.main('4')
        self.assert_files(['@_-1--2--3-[4]-5--6-[7]'])
        self.main('s4')
        self.assert_files(['@_-1--2--3-$4$-5--6-[7]'])
    def test_seen_interval(self) :
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])
        self.main('1-5')
        self.assert_files(['@_[1][2][3][4][5]-6-[7]'])
        self.main('s2-4')
        self.assert_files(['@_[1]$2$$3$$4$[5]-6-[7]'])
    def test_seen_interval2(self) :
        self.main('7')
        self.assert_files(['@_-1--2--3--4--5--6-[7]'])
        self.main('1-4')
        self.assert_files(['@_[1][2][3][4]-5--6-[7]'])
        self.main('s2-5')
        self.assert_files(['@_[1]$2$$3$$4$!5!-6-[7]'])
    def test_comma(self) :
        self.main('1,4,7')
        self.assert_files(['@_[1]-2--3-[4]-5--6-[7]'])
    def test_comma_interval_1(self) :
        self.main('1,4-6,8')
        self.assert_files(['@_[1]-2--3-[4][5][6]-7-[8]'])
    def test_comma_interval_2(self) :
        self.main('113-124,139-145,152-155')
        self.assert_files(['@_-101--102--103--104--105--106--107--108--109--110--111--112-[113][114][115][116][117][118][119][120]','@_[121][122][123][124]-125--126--127--128--129--130--131--132--133--134--135--136--137--138-[139][140]','@_[141][142][143][144][145]-146--147--148--149--150--151-[152][153][154][155]'])
    def test_comma_interval_multiple(self) :
        self.main('1,4-6,8','s3-4,6-8')
        self.assert_files(['@_[1]-2-!3!$4$[5]$6$!7!$8$'])
    def test_consolidate_multiple_end(self) :
        self.touch(['[7]','[14][9]','-17-'])
        self.assert_files(['[7]','[14][9]','-17-'])
        self.main()
        self.assert_files(['-01--02--03--04--05--06-[07]-08-[09]-10--11--12--13-[14]-15--16--17-'])
    def test_consolidate_multiple_end_2(self) :
        self.touch(['[7]','@_[14][9]','-22-'])
        self.assert_files(['[7]','@_[14][9]','-22-'])
        self.main()
        self.assert_files(['@_-01--02--03--04--05--06-[07]-08-[09]-10--11--12--13-[14]-15--16--17--18--19--20-','@_-21--22-'])
    def test_suppression_empty(self) :
        self.main('-7')
        self.assert_files(['@_-1--2--3--4--5--6--7-'])

    def test_subdir_basic(self):
        self.main('s1:7')
        self.assert_files(['@_s01_-1--2--3--4--5--6-[7]'])
        self.main('s1~SUB01')
        self.assert_files(['@_s01~SUB01'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')

    def test_subdir_basic_other_order(self):
        self.main('s1~SUB01')
        self.assert_files(['@_s01~SUB01'])
        self.main('s1:7')
        self.assert_files(['@_s01~SUB01'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')

    def test_subdir_multiple(self):
        self.main('s1:7','5')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01_-1--2--3--4--5--6-[7]'])
        self.main('s1~SUB01')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01~SUB01'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')
        self.main('s002~SUB002','s2:e10','s3:4')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01~SUB01','@_s02~SUB002','@_s03_-1--2--3-[4]'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')
        self.assert_files(['@_-01--02--03--04--05--06--07--08--09--10-+'],subdir='SUB002')

    def test_flatten(self):
        self.main('s1:7','5','s1~SUB01','s002~SUB002','s2:e10','s3:4')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01~SUB01','@_s02~SUB002','@_s03_-1--2--3-[4]'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')
        self.assert_files(['@_-01--02--03--04--05--06--07--08--09--10-+'],subdir='SUB002')
        self.main('flatten')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01_-1--2--3--4--5--6-[7]','@_s02_-01--02--03--04--05--06--07--08--09--10-+','@_s03_-1--2--3-[4]'])
        self.assert_files([],subdir='SUB01')
        self.assert_files([],subdir='SUB002')

    def test_flatten_f(self):
        self.main('s1:7','5','s1~SUB01','s002~SUB002','s2:e10','s3:4')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01~SUB01','@_s02~SUB002','@_s03_-1--2--3-[4]'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')
        self.assert_files(['@_-01--02--03--04--05--06--07--08--09--10-+'],subdir='SUB002')
        self.main('f')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01_-1--2--3--4--5--6-[7]','@_s02_-01--02--03--04--05--06--07--08--09--10-+','@_s03_-1--2--3-[4]'])
        self.assert_files([],subdir='SUB01')
        self.assert_files([],subdir='SUB002')

    def test_text(self):
        self.main('s1:7','5','s1~SUB01','s002~SUB002','s2:e10','s3:4','s3:113-124,139-145,152-155','s3:s123-126')
        self.assert_files(['@_-1--2--3--4-[5]','@_s01~SUB01','@_s02~SUB002','@_s03_-001--002--003-[004]-005--006--007--008--009--010--011--012--013--014--015--016--017--018--019--020-','@_s03_-101--102--103--104--105--106--107--108--109--110--111--112-[113][114][115][116][117][118][119][120]','@_s03_[121][122]$123$$124$!125!!126!-127--128--129--130--131--132--133--134--135--136--137--138-[139][140]','@_s03_[141][142][143][144][145]-146--147--148--149--150--151-[152][153][154][155]'])
        self.assert_files(['@_-1--2--3--4--5--6-[7]'],subdir='SUB01')
        self.assert_files(['@_-01--02--03--04--05--06--07--08--09--10-+'],subdir='SUB002')
        self.main('text')
        self.assert_out([
            ' 1   2   3   4  [5]',
            '',
            's01 (SUB01):',
            ' 1   2   3   4   5   6  [7]',
            '',
            's02 (SUB002):',
            ' 01   02   03   04   05   06   07   08   09   10  ++',
            '',
            's03:',
            ' 001   002   003  [004]  005   006   007   008   009   010   011   012   013   014   015   016   017   018   019   020 ',
            ' 021   022   023   024   025   026   027   028   029   030   031   032   033   034   035   036   037   038   039   040 ',
            ' 041   042   043   044   045   046   047   048   049   050   051   052   053   054   055   056   057   058   059   060 ',
            ' 061   062   063   064   065   066   067   068   069   070   071   072   073   074   075   076   077   078   079   080 ',
            ' 081   082   083   084   085   086   087   088   089   090   091   092   093   094   095   096   097   098   099   100 ',
            ' 101   102   103   104   105   106   107   108   109   110   111   112  [113] [114] [115] [116] [117] [118] [119] [120]',
            '[121] [122] $123$ $124$ !125! !126!  127   128   129   130   131   132   133   134   135   136   137   138  [139] [140]',
            '[141] [142] [143] [144] [145]  146   147   148   149   150   151  [152] [153] [154] [155]',
            '',
            ])

if __name__ == '__main__' :
    unittest.main()


