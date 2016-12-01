#!/usr/local/bin/python
import os
# import ycm_core

# return the filename in the path without extension
def findFileName(path, ext):
  name = ''
  for projFile in os.listdir(path):
    # cocoapods will generate _Pods.xcodeproj as well
    if projFile.endswith(ext) and not projFile.startswith('_Pods'):
      name= projFile[:-len(ext):]
  return name

# WARNING!! No / in the end
def DirectoryOfThisScript():
  return os.path.dirname( os.path.abspath( __file__ ) )

def findProjectName(working_directory):
  projectName = findFileName(working_directory, '.xcodeproj')

  if len(projectName) <= 0:
    # cocoapod projects
    projectName = findFileName(working_directory, '.podspec')
  return projectName

flags = ['-x', 'objective-c',
        '-arch', 'arm64',
        '-fmodules',
        '-miphoneos-version-min=9.3',
        '-isysroot', '/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk'
        ]

SOURCE_EXTENSIONS = [ '.cpp', '.cxx', '.cc', '.c', '.m', '.mm' ]

# Set this to the absolute path to the folder (NOT the file!) containing the
# compile_commands.json file to use that instead of 'flags'. See here for
# more details: http://clang.llvm.org/docs/JSONCompilationDatabase.html
#
# You can get CMake to generate this file for you by adding:
#   set( CMAKE_EXPORT_COMPILE_COMMANDS 1 )
# to your CMakeLists.txt file.
#
# Most projects will NOT need to set this to anything; you can just change the
# 'flags' list of compilation flags. Notice that YCM itself uses that approach.
compilation_database_folder = ''

# if os.path.exists( compilation_database_folder ):
  # database = ycm_core.CompilationDatabase( compilation_database_folder )
# else:
# we don't use compilation database
database = None

SOURCE_EXTENSIONS = [ '.cpp', '.cxx', '.cc', '.c', '.m', '.mm' ]

def Subdirectories(directory):
  res = []
  for path, subdirs, files in os.walk(directory):
    for name in subdirs:
      item = os.path.join(path, name)
      res.append(item)
  return res

def sorted_ls(path):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
    return list(sorted(os.listdir(path), key=mtime))

def IncludeClangInXCToolChain(flags, working_directory):
  if not working_directory:
    return list( flags )

  new_flags = list(flags)
  # '-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/7.0.2/include',
  path = '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/'
  clangPath = sorted_ls(path)[::-1] # newest file first

  includePath = ''
  if (len(clangPath) > 0):
    includePath = os.path.join('', *[path, clangPath[0], 'include'])
    new_flags.append('-I'+includePath)
  return new_flags

def IncludeFlagsOfFrameworkHeaders( flags, working_directory ):
  if not working_directory:
    return flags

  new_flags = []
  path_flag = '-ProductFrameworkInclude'
  derivedDataPath = os.path.expanduser('~/Library/Developer/Xcode/DerivedData/')
  simulatorPaths = ['Build/Intermediates/CodeCoverage/Products/Debug-iphonesimulator/', # if you enable CodeCoverage, the framework of test target will be put in coverage folder, strange
                    'Build/Products/Debug-iphonesimulator/']
  # find the project name
  projectName = findProjectName(working_directory)
  if len(projectName) <= 0:
    return flags

  # add all frameworks in the /Build/Products/Debug-iphonesimulator/xxx/xxx.framework
  for flag in flags:
    if not flag.startswith( path_flag ):
      new_flags.append(flag)
      continue
    projectPath = ''
    # search ~/Library/Developer/Xcode/DerivedData/ to find <project_name>-dliwlpgcvwijijcdxarawwtrfuuh
    derivedPath = sorted_ls(derivedDataPath)[::-1] # newest file first
    for productPath in derivedPath:
      if productPath.lower().startswith( projectName.lower() ):
        for simulatorPath in simulatorPaths:
          projectPath = os.path.join('', *[derivedDataPath, productPath, simulatorPath])
          if (len(projectPath) > 0) and os.path.exists(projectPath):
            break # the lastest product is what we want (really?)

    if (len(projectPath) <= 0) or not os.path.exists(projectPath):
      continue

    # iterate through all frameworks folders /Debug-iphonesimulator/xxx/xxx.framework
    for frameworkFolder in os.listdir(projectPath):
      frameworkPath = os.path.join('', projectPath, frameworkFolder)
      # framwork folder '-F/Debug-iphonesimulator/<framework-name>'
      # solve <Kiwi/KiwiConfigurations.h> not found problem
      new_flags.append('-F'+frameworkPath)

      # the framework name might be different than folder name
      # we need to iterate all frameworks
      for frameworkFile in os.listdir(frameworkPath):
        if frameworkFile.endswith('framework'):
          # include headers '-I/Debug-iphonesimulator/xxx/yyy.framework/Headers'
          # allow you to use #import "Kiwi.h". NOT REQUIRED, but I am too lazy to change existing codes
          new_flags.append('-I' + os.path.join('', frameworkPath, frameworkFile,'Headers'))

  return new_flags


def IncludeFlagsOfSubdirectory( flags, working_directory ):
  if not working_directory:
    return list( flags )
  new_flags = []
  make_next_include_subdir = False
  path_flags = [ '-ISUB']
  for flag in flags:
    # include the directory of flag as well
    new_flag = [flag.replace('-ISUB', '-I')]

    if make_next_include_subdir:
      make_next_include_subdir = False
      for subdir in Subdirectories(os.path.join(working_directory, flag)):
        new_flag.append('-I')
        new_flag.append(subdir)

    for path_flag in path_flags:
      if flag == path_flag:
        make_next_include_subdir = True
        break

      if flag.startswith( path_flag ):
        path = flag[ len( path_flag ): ]
        for subdir in Subdirectories(os.path.join(working_directory, path)):
            new_flag.append('-I' + subdir)
        break

    new_flags =new_flags + new_flag
  return new_flags

def MakeRelativePathsInFlagsAbsolute( flags, working_directory ):
  if not working_directory:
    return list( flags )
  #add include subfolders as well
  flags = IncludeFlagsOfSubdirectory( flags, working_directory )

  #include framework header in derivedData/.../Products
  flags = IncludeFlagsOfFrameworkHeaders( flags, working_directory )

  #include libclang header in xctoolchain
  flags = IncludeClangInXCToolChain( flags, working_directory )
  new_flags = []
  make_next_absolute = False
  path_flags = [ '-isystem', '-I', '-iquote', '--sysroot=' ]
  for flag in flags:
    new_flag = flag

    if make_next_absolute:
      make_next_absolute = False
      if not flag.startswith( '/' ):
        new_flag = os.path.join( working_directory, flag )

    for path_flag in path_flags:
      if flag == path_flag:
        make_next_absolute = True
        break

      if flag.startswith( path_flag ):
        path = flag[ len( path_flag ): ]
        new_flag = path_flag + os.path.join( working_directory, path )
        break

    if new_flag:
      new_flags.append( new_flag )
  return new_flags


def IsHeaderFile( filename ):
  extension = os.path.splitext( filename )[ 1 ]
  return extension in [ '.h', '.hxx', '.hpp', '.hh' ]


def GetCompilationInfoForFile( filename ):
  # The compilation_commands.json file generated by CMake does not have entries
  # for header files. So we do our best by asking the db for flags for a
  # corresponding source file, if any. If one exists, the flags for that file
  # should be good enough.
  if IsHeaderFile( filename ):
    basename = os.path.splitext( filename )[ 0 ]
    for extension in SOURCE_EXTENSIONS:
      replacement_file = basename + extension
      if os.path.exists( replacement_file ):
        compilation_info = database.GetCompilationInfoForFile(
          replacement_file )
        if compilation_info.compiler_flags_:
          return compilation_info
    return None
  return database.GetCompilationInfoForFile( filename )

def FlagsForFile( filename, **kwargs ):
  return {
    'flags': flags,
    'do_cache': True
  }

if __name__ == "__main__":
  print flags
  # flags = [
  # '-D__IPHONE_OS_VERSION_MIN_REQUIRED=70000',
  # '-x',
  # 'objective-c',
  # '-ProductFrameworkInclude',
  # '-ProductFrameworkInclude',
  # '-F/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks',
  # '-ISUB./Pods/Headers/Public',
  # '-MMD',
  # ]

  # print IncludeClangInXCToolChain(flags, DirectoryOfThisScript())

# if __name__ == "__main__":
  # flags = [
  # '-D__IPHONE_OS_VERSION_MIN_REQUIRED=70000',
  # '-x',
  # 'objective-c',
  # '-ProductFrameworkInclude',
  # '-ProductFrameworkInclude',
  # '-F/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks',
  # '-ISUB./Pods/Headers/Public',
  # '-MMD',
  # ]

  # print IncludeFlagsOfFrameworkHeaders( flags, DirectoryOfThisScript() )

# if __name__ == '__main__':
    # # res = subdirectory( DirectoryOfThisScript())
  # flags = [
  # '-D__IPHONE_OS_VERSION_MIN_REQUIRED=70000',
  # '-x',
  # 'objective-c',
  # '-F/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks',
  # '-ISUB./Pods/Headers/Public',
  # '-MMD',
  # ]

  # print IncludeFlagsOfSubdirectory( flags, DirectoryOfThisScript() )
  # res = IncludeFlagsOfSubdirectory( flags, DirectoryOfThisScript() )
  # escaped = []
  # for flag in res:
    # if " " not in flag:
      # escaped.append(flag)
  # print ' '.join(escaped)




