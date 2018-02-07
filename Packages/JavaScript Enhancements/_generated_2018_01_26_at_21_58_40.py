import sublime, sublime_plugin
import os, sys, imp, platform, json, traceback, threading, urllib, shutil, re, time
from shutil import copyfile
from threading import Timer
from os import environ
from subprocess import Popen, PIPE

PLUGIN_VERSION = "0.13.17"

PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))
PACKAGE_NAME = os.path.basename(PACKAGE_PATH)
SUBLIME_PACKAGES_PATH = os.path.dirname(PACKAGE_PATH)

JC_SETTINGS_FOLDER_NAME = "javascript_completions"
JC_SETTINGS_FOLDER = os.path.join(PACKAGE_PATH, "helper", JC_SETTINGS_FOLDER_NAME)

PROJECT_FOLDER_NAME = "project"
PROJECT_FOLDER = os.path.join(PACKAGE_PATH, PROJECT_FOLDER_NAME)
socket_server_list = dict()

HELPER_FOLDER_NAME = "helper"
HELPER_FOLDER = os.path.join(PACKAGE_PATH, HELPER_FOLDER_NAME)

BOOKMARKS_FOLDER = os.path.join(HELPER_FOLDER, 'bookmarks')

WINDOWS_BATCH_FOLDER = os.path.join(PACKAGE_PATH, 'windows_batch')

platform_switcher = {"osx": "OSX", "linux": "Linux", "windows": "Windows"}
os_switcher = {"osx": "darwin", "linux": "linux", "windows": "win"}
PLATFORM = platform_switcher.get(sublime.platform())
PLATFORM_ARCHITECTURE = "64bit" if platform.architecture()[0] == "64bit" else "32bit" 

PROJECT_TYPE_SUPPORTED = ['empty', 'angularv1', 'angularv2', 'cordova', 'express', 'ionicv1', 'ionicv2', 'react', 'react-native', 'yeoman']

class Hook(object):
  hook_list = {}

  @staticmethod
  def add (hook_name, hook_func, priority = 10) :
    if not hook_name in Hook.hook_list :
      Hook.hook_list[hook_name] = []

    Hook.hook_list[hook_name].append({
      "hook_func": hook_func,
      "priority": priority if priority >= 0 else 0
    })

    Hook.hook_list[hook_name] = sorted(Hook.hook_list[hook_name], key=lambda hook: hook["priority"])

  @staticmethod
  def apply(hook_name, value='', *args, **kwargs) :

    args = (value,) + args

    if hook_name in Hook.hook_list :
      for hook in Hook.hook_list[hook_name] :
        hook["hook_func"](*args, **kwargs)
        #value = hook["hook_func"](*args, **kwargs)
        #args = (value,) + args[1:]

    #return value

  @staticmethod
  def count(hook_name) :

    if hook_name in Hook.hook_list :
      return len(Hook.hook_list[hook_name])
    return 0

  @staticmethod
  def removeHook(hook_name, hook_func, priority = -1) :

    if hook_name in Hook.hook_list :
      if priority >= 0 :
        hook = { 
          "hook_func": hook_func, 
          "priority": priority 
        }
        while hook in Hook.hook_list[hook_name] : 
          Hook.hook_list[hook_name].remove(hook)
      else :
         for hook in Hook.hook_list[hook_name] :
          if hook["hook_func"] == hook_func :
            Hook.hook_list[hook_name].remove(hook)

  @staticmethod
  def removeAllHook(hook_name) :

    if hook_name in Hook.hook_list :
      Hook.hook_list[hook_name] = []
      

import sublime

class AnimationLoader(object):
  def __init__(self, animation, sec, str_before="", str_after=""):
    self.animation = animation
    self.sec = sec
    self.animation_length = len(animation)
    self.str_before = str_before
    self.str_after = str_after
    self.cur_anim = 0
  def animate(self):
    sublime.active_window().status_message(self.str_before+self.animation[self.cur_anim % self.animation_length]+self.str_after)
    self.cur_anim = self.cur_anim + 1
  def on_complete(self):
    sublime.active_window().status_message("")
from threading import Timer

class RepeatedTimer(object):
  def __init__(self, interval, function, *args, **kwargs):
    self._timer     = None
    self.interval   = interval
    self.function   = function
    self.args       = args
    self.kwargs     = kwargs
    self.is_running = False
    self.start()

  def _run(self):
    self.is_running = False
    self.start()
    self.function(*self.args, **self.kwargs)

  def start(self):
    if not self.is_running:
      self._timer = Timer(self.interval, self._run)
      self._timer.start()
      self.is_running = True

  def stop(self):
    self._timer.cancel()
    self.is_running = False
import subprocess, threading
import sys, imp, codecs, shlex, os, json, traceback, tempfile

NODE_JS_EXEC = "node"
NPM_EXEC = "npm"
YARN_EXEC = "yarn"

NODE_MODULES_FOLDER_NAME = "node_modules"
NODE_MODULES_PATH = os.path.join(PACKAGE_PATH, NODE_MODULES_FOLDER_NAME)
NODE_MODULES_BIN_PATH = os.path.join(NODE_MODULES_PATH, ".bin")

class NodeJS(object):
  def __init__(self, check_local = False):
    self.check_local = check_local
    self.node_js_path = ""

    if self.check_local :
      settings = get_project_settings()
      if settings :
        self.node_js_path = settings["project_settings"]["node_js_custom_path"] or javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
      else :
        self.node_js_path = javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
    else :
      self.node_js_path = javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC

  def eval(self, js, eval_type="eval", strict_mode=False):

    js = ("'use strict'; " if strict_mode else "") + js
    eval_type = "--eval" if eval_type == "eval" else "--print"

    args = [self.node_js_path, eval_type, js]

    result = Util.execute(args[0], args[1:])

    if result[0] :
      return result[1]

    raise Exception(result[1])

  def getCurrentNodeJSVersion(self) :

    args = [self.node_js_path, "-v"]

    result = Util.execute(args[0], args[1:])

    if result[0] :
      return result[1].strip()

    raise Exception(result[1])

  def execute(self, command, command_args, is_from_bin=False, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[], bin_path="", use_node=True) :

    if sublime.platform() == 'windows':
      if is_from_bin :
        args = [os.path.join( (bin_path or NODE_MODULES_BIN_PATH), command+".cmd")] + command_args
      else :
        args = ([self.node_js_path] if use_node else []) + [os.path.join( (bin_path or NODE_MODULES_BIN_PATH), command)] + command_args
    else :
      args = ([self.node_js_path] if use_node else []) + [os.path.join( (bin_path or NODE_MODULES_BIN_PATH), command)] + command_args
    
    return Util.execute(args[0], args[1:], chdir=chdir, wait_terminate=wait_terminate, func_stdout=func_stdout, args_func_stdout=args_func_stdout)
    
  def execute_check_output(self, command, command_args, is_from_bin=False, use_fp_temp=False, use_only_filename_view_flow=False, fp_temp_contents="", is_output_json=False, chdir="", clean_output_flow=False, bin_path="", use_node=True) :

    fp = None
    args = ""

    if use_fp_temp :
      
      if sublime.platform() == "windows":
        fp = tempfile.NamedTemporaryFile(delete=False)
        fp.write(str.encode(fp_temp_contents))
        fp.close()
      else :
        fp = tempfile.NamedTemporaryFile()
        fp.write(str.encode(fp_temp_contents))
        fp.flush()

    command_args_list = list()
    for command_arg in command_args :
      if command_arg == ":temp_file":
        command_arg = fp.name
      command_args_list.append(shlex.quote(command_arg) if sublime.platform() != 'windows' else json.dumps(command_arg))
    command_args = " ".join(command_args_list)

    if sublime.platform() == 'windows':
      if is_from_bin :
        args = json.dumps(os.path.join((bin_path or NODE_MODULES_BIN_PATH), command)+'.cmd')+' '+command_args+(' < '+json.dumps(fp.name) if fp and not use_only_filename_view_flow else "")
      else :
        args = ( json.dumps(self.node_js_path)+" " if use_node else "")+json.dumps(os.path.join((bin_path or NODE_MODULES_BIN_PATH), command))+" "+command_args+(" < "+json.dumps(fp.name) if fp and not use_only_filename_view_flow else "")
    else:
      args = ( shlex.quote(self.node_js_path)+" " if use_node else "")+shlex.quote(os.path.join((bin_path or NODE_MODULES_BIN_PATH), command))+" "+command_args+(" < "+shlex.quote(fp.name) if fp and not use_only_filename_view_flow else "")

    #print(args)
      
    old_env = os.environ.copy()

    new_env = old_env.copy()
    new_env["PATH"] = new_env["PATH"] + javascriptCompletions.get("PATH")

    # update the PATH environment variable
    os.environ.update(new_env)

    try:
      output = None
      result = None

      owd = os.getcwd()
      if chdir :
        os.chdir(chdir)

      output = subprocess.check_output(
          args, shell=True, stderr=subprocess.STDOUT, timeout=10
      )
      
      if sublime.platform() == "windows" and use_fp_temp: 
        os.remove(fp.name)

      # reset the PATH environment variable
      os.environ.update(old_env)

      if chdir:
        os.chdir(owd)

      if clean_output_flow :
        out = output.decode("utf-8", "ignore").strip()
        out = out.split("\n")
        # if len(out) > 1 and out[3:][0].startswith("Started a new flow server: -flow is still initializing; this can take some time. [processing] "):
        #   out = out[3:]
        #   out[0] = out[0].replace("Started a new flow server: -flow is still initializing; this can take some time. [processing] ", "")[1:]
        #   out = "\n".join(out)
        #   print(out)
        #   result = json.loads(out) if is_output_json else out
        # elif len(out) > 1 and out[3:][0].startswith("Started a new flow server: -flow is still initializing; this can take some time. [merging inference] "):
        #   out = out[3:]
        #   out[0] = out[0].replace("Started a new flow server: -flow is still initializing; this can take some time. [merging inference] ", "")[1:]
        #   out = "\n".join(out)
        #   result = json.loads(out) if is_output_json else out
        # elif len(out) > 1 and out[3:][0].startswith("Started a new flow server: -"):
        #   out = out[3:]
        #   out[0] = out[0].replace("Started a new flow server: -", "")
        #   out = "\n".join(out)
        #   result = json.loads(out) if is_output_json else out
        out = out[-1]
        if '{"flowVersion":"' in out :
          index = out.index('{"flowVersion":"')
          out = out[index:]
          result = json.loads(out) if is_output_json else out
        else :
          return [False, {}]
      else :
        try:
          result = json.loads(output.decode("utf-8", "ignore")) if is_output_json else output.decode("utf-8", "ignore")
        except ValueError as e:
          print(traceback.format_exc())
          print(output.decode("utf-8", "ignore"))
          return [False, {}]

      if use_fp_temp :
        fp.close()

      return [True, result]
    except subprocess.CalledProcessError as e:
      print(traceback.format_exc())

      if e.output:
        output_error_message = e.output.decode("utf-8", "ignore").strip()
        output_error_message = output_error_message.split("\n")
        output_error_message = "\n".join(output_error_message[:-2]) if '{"flowVersion":"' in output_error_message[-1] else "\n".join(output_error_message)

        print(e.output)
        sublime.active_window().status_message(output_error_message)

      # reset the PATH environment variable
      os.environ.update(old_env)

      if sublime.platform() == "windows" and use_fp_temp: 
        os.remove(fp.name)

      try:
        result = json.loads(output.decode("utf-8", "ignore")) if is_output_json else output.decode("utf-8", "ignore")
        if use_fp_temp :
          fp.close()
        return [False, result]
      except:
        #print(traceback.format_exc())
        if use_fp_temp :
          fp.close()

        return [False, None]

    except subprocess.TimeoutExpired as e:
      # reset the PATH environment variable
      os.environ.update(old_env)

      #print(traceback.format_exc())

      if use_fp_temp :
        if sublime.platform() == "windows": 
          os.remove(fp.name)
        else:
          fp.close()
      return [False, None]

    except:

      # reset the PATH environment variable
      os.environ.update(old_env)

      print(traceback.format_exc())

      if use_fp_temp :
        if sublime.platform() == "windows": 
          os.remove(fp.name)
        else:
          fp.close()
      return [False, None]

class NPM(object):
  def __init__(self, check_local = False):
    self.check_local = check_local
    self.npm_path = ""
    self.yarn_path = ""
    self.cli_path = ""
    self.node_js_path = ""

    if self.check_local :
      settings = get_project_settings()
      if settings :
        self.node_js_path = settings["project_settings"]["node_js_custom_path"] or javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
        self.npm_path = settings["project_settings"]["npm_custom_path"] or javascriptCompletions.get("npm_custom_path") or NPM_EXEC
        self.yarn_path = settings["project_settings"]["yarn_custom_path"] or javascriptCompletions.get("yarn_custom_path") or YARN_EXEC

        if settings["project_settings"]["use_yarn"] and self.yarn_path :
          self.cli_path = self.yarn_path
        else :
          self.cli_path = self.npm_path

      else :
        self.node_js_path = javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
        self.npm_path = javascriptCompletions.get("npm_custom_path") or NPM_EXEC
        self.yarn_path = javascriptCompletions.get("yarn_custom_path") or YARN_EXEC

        self.cli_path = self.npm_path
    else :
      self.node_js_path = javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
      self.npm_path = javascriptCompletions.get("npm_custom_path") or NPM_EXEC
      self.yarn_path = javascriptCompletions.get("yarn_custom_path") or YARN_EXEC

      self.cli_path = self.npm_path

  def execute(self, command, command_args, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[]) :

    args = []

    if sublime.platform() == 'windows':
      args = [self.cli_path, command] + command_args
    else :
      args = [self.cli_path, command] + command_args
    
    return Util.execute(args[0], args[1:], chdir=chdir, wait_terminate=wait_terminate, func_stdout=func_stdout, args_func_stdout=args_func_stdout)

  def install_all(self, save=False, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[]) :

    return self.execute('install', (["--save"] if save else []), chdir=(PACKAGE_PATH if not chdir else chdir), wait_terminate=wait_terminate, func_stdout=func_stdout, args_func_stdout=args_func_stdout)

  def update_all(self, save=False, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[]) :

    return self.execute('update', (["--save"] if save else []), chdir=(PACKAGE_PATH if not chdir else chdir), wait_terminate=wait_terminate, func_stdout=func_stdout, args_func_stdout=args_func_stdout)

  def install(self, package_name, save=False, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[]) :
    
    return self.execute('install', (["--save"] if save else []) + [package_name], chdir=(PACKAGE_PATH if not chdir else chdir), wait_terminate=wait_terminate, func_stdout=func_stdout, args_func_stdout=args_func_stdout)
  
  def update(self, package_name, save=False, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[]) :

    return self.execute('update', (["--save"] if save else []) + [package_name], chdir=(PACKAGE_PATH if not chdir else chdir), wait_terminate=wait_terminate, func_stdout=func_stdout, args_func_stdout=args_func_stdout)

  def getPackageJson(self):

    package_json_path = ""
    settings = get_project_settings()

    if self.check_local and settings and os.path.isfile( os.path.join(settings["project_dir_name"], "package.json") ) :
      package_json_path = os.path.join(settings["project_dir_name"], "package.json")
    elif self.check_local and (not settings or not os.path.isfile( os.path.join(settings["project_dir_name"], "package.json") ) ) :
      return None
    else :
      package_json_path = os.path.join(PACKAGE_PATH, "package.json")

    return Util.open_json(package_json_path)

  def getCurrentNPMVersion(self) :

    if sublime.platform() == 'windows':
      args = [self.cli_path, "-v"]
    else :
      args = [self.cli_path, "-v"]

    result = Util.execute(args[0], args[1:])

    if result[0] :
      return result[1].strip()

    raise Exception(result[1])

import sublime, sublime_plugin
import re, urllib, shutil, traceback, threading, time, os, hashlib, json, multiprocessing, shlex

class Util(object) :

  multiprocessing_list = []

  @staticmethod
  def download_and_save(url, where_to_save) :
    if where_to_save :
      try :
        request = urllib.request.Request(url)
        request.add_header('User-agent', r'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1')
        with urllib.request.urlopen(request) as response :
          with open(where_to_save, 'wb+') as out_file :
            shutil.copyfileobj(response, out_file)
            return True
      except Exception as e:
        traceback.print_exc()
    return False

  @staticmethod
  def open_json(path):
    with open(path) as json_file :    
      try :
        return json.load(json_file)
      except Exception as e :
        print("Error: "+traceback.format_exc())
    return None

  @staticmethod
  def check_thread_is_alive(thread_name) :
    for thread in threading.enumerate() :
      if thread.getName() == thread_name and thread.is_alive() :
        return True
    return False

  @staticmethod
  def create_and_start_thread(target, thread_name="", args=[], kwargs={}, daemon=True) :
    if not Util.check_thread_is_alive(thread_name) :
      thread = threading.Thread(target=target, name=thread_name, args=args, kwargs=kwargs, daemon=daemon)
      thread.start()
      return thread
    return None

  @staticmethod
  def check_process_is_alive(process_name) :
    Util.multiprocessing_list
    for process in Util.multiprocessing_list :
      if process.name == process_name :
        if process.is_alive() :
          return True
        else :
          Util.multiprocessing_list.remove(process)
    return False

  @staticmethod
  def create_and_start_process(target, process_name="", args=[], kwargs={}, daemon=True) :
    Util.multiprocessing_list
    if not Util.check_process_is_alive(process_name) :
      process = multiprocessing.Process(target=target, name=process_name, args=args, kwargs=kwargs, daemon=daemon)
      process.start()
      Util.multiprocessing_list.append(process)
      return process
    return None

  @staticmethod
  def setTimeout(time, func):
    timer = threading.Timer(time, func)
    timer.start()
    return timer

  @staticmethod
  def checksum_sha1(fname):
    hash_sha1 = hashlib.sha1()
    with open(fname, "rb") as f:
      for chunk in iter(lambda: f.read(4096), b""):
        hash_sha1.update(chunk)
    return hash_sha1.hexdigest()

  @staticmethod
  def checksum_sha1_equalcompare(fname1, fname2):
    return Util.checksum_sha1(fname1) == Util.checksum_sha1(fname2)

  @staticmethod
  def split_string_and_find(string_to_split, search_value, split_delimiter=" ") :
    string_splitted = string_to_split.split(split_delimiter)
    return Util.indexOf(string_splitted, search_value) 

  @staticmethod
  def split_string_and_find_on_multiple(string_to_split, search_values, split_delimiter=" ") :
    string_splitted = string_to_split.split(split_delimiter)
    for search_value in search_values :
      index = Util.indexOf(string_splitted, search_value) 
      if index >= 0 :
        return index
    return -1

  @staticmethod
  def split_string_and_findLast(string_to_split, search_value, split_delimiter=" ") :
    string_splitted = string_to_split.split(split_delimiter)
    return Util.lastIndexOf(string_splitted, search_value) 

  @staticmethod
  def indexOf(list_to_search, search_value) :
    index = -1
    try :
      index = list_to_search.index(search_value)
    except Exception as e:
      pass
    return index

  @staticmethod
  def lastIndexOf(list_to_search, search_value) :
    index = -1
    list_to_search_reversed = reversed(list_to_search)
    list_length = len(list_to_search)
    try :
      index = next(i for i,v in zip(range(list_length-1, 0, -1), list_to_search_reversed) if v == search_value)
    except Exception as e:
      pass
    return index

  @staticmethod
  def firstIndexOfMultiple(list_to_search, search_values) :
    index = -1
    string = ""
    for search_value in search_values :
      index_search = Util.indexOf(list_to_search, search_value)
      if index_search >= 0 and index == -1 :
        index = index_search
        string = search_value
      elif index_search >= 0 :
        index = min(index, index_search)
        string = search_value
    return {
      "index": index,
      "string": string
    }

  @staticmethod
  def find_and_get_pre_string_and_first_match(string, search_value) :
    result = None
    index = Util.indexOf(string, search_value)
    if index >= 0 :
      result = string[:index+len(search_value)]
    return result

  @staticmethod
  def find_and_get_pre_string_and_matches(string, search_value) :
    result = None
    index = Util.indexOf(string, search_value)
    if index >= 0 :
      result = string[:index+len(search_value)]
      string = string[index+len(search_value):]
      count_occ = string.count(search_value)
      i = 0
      while i < count_occ :
        result += " "+search_value
        i = i + 1
    return result

  @staticmethod
  def get_region_scope_first_match(view, scope, selection, selector) :
    scope = Util.find_and_get_pre_string_and_first_match(scope, selector)
    if scope :
      for region in view.find_by_selector(scope) :
        if region.contains(selection):
          selection.a = region.begin()
          selection.b = selection.a
          return {
            "scope": scope,
            "region": region,
            "region_string": view.substr(region),
            "region_string_stripped": view.substr(region).strip(),
            "selection": selection
          }
    return None

  @staticmethod
  def get_region_scope_last_match(view, scope, selection, selector) :
    scope = Util.find_and_get_pre_string_and_matches(scope, selector)
    if scope :
      for region in view.find_by_selector(scope) :
        if region.contains(selection):
          selection.a = region.begin()
          selection.b = selection.a
          return {
            "scope": scope,
            "region": region,
            "region_string": view.substr(region),
            "region_string_stripped": view.substr(region).strip(),
            "selection": selection
          }
    return None

  @staticmethod
  def find_regions_on_same_depth_level(view, scope, selection, selectors, depth_level, forward) :
    scope_splitted = scope.split(" ")
    regions = list()
    add_unit = 1 if forward else -1
    if len(scope_splitted) >= depth_level :  
      for selector in selectors :
        while Util.indexOf(scope_splitted, selector) == -1 :
          if selection.a == 0 or len(scope_splitted) < depth_level :
            return list()
          selection.a = selection.a + add_unit
          selection.b = selection.a 
          scope = view.scope_name(selection.begin()).strip()
          scope_splitted = scope.split(" ")
        region = view.extract_scope(selection.begin())
        regions.append({
          "scope": scope,
          "region": region,
          "region_string": view.substr(region),
          "region_string_stripped": view.substr(region).strip(),
          "selection": selection
        })
    return regions

  @staticmethod
  def get_current_region_scope(view, selection) :
    scope = view.scope_name(selection.begin()).strip()
    for region in view.find_by_selector(scope) :
      if region.contains(selection):
        selection.a = region.begin()
        selection.b = selection.a
        return {
          "scope": scope,
          "region": region,
          "region_string": view.substr(region),
          "region_string_stripped": view.substr(region).strip(),
          "selection": selection
        }
    return None

  @staticmethod
  def get_parent_region_scope(view, selection) :
    scope = view.scope_name(selection.begin()).strip()
    scope = " ".join(scope.split(" ")[:-1])
    for region in view.find_by_selector(scope) :
      if region.contains(selection):
        selection.a = region.begin()
        selection.b = selection.a
        return {
          "scope": scope,
          "region": region,
          "region_string": view.substr(region),
          "region_string_stripped": view.substr(region).strip(),
          "selection": selection
        }
    return None

  @staticmethod
  def get_specified_parent_region_scope(view, selection, parent) :
    scope = view.scope_name(selection.begin()).strip()
    scope = scope.split(" ")
    index_parent = Util.lastIndexOf(scope, parent)
    scope = " ".join(scope[:index_parent+1])
    for region in view.find_by_selector(scope) :
      if region.contains(selection):
        selection.a = region.begin()
        selection.b = selection.a
        return {
          "scope": scope,
          "region": region,
          "region_string": view.substr(region),
          "region_string_stripped": view.substr(region).strip(),
          "selection": selection
        }
    return None

  @staticmethod
  def cover_regions(regions) :
    first_region = regions[0]
    other_regions = regions[1:]
    for region in other_regions :
      first_region = first_region.cover(region)
    return first_region

  @staticmethod
  def rowcol_to_region(view, row, endrow, col, endcol):
    start = view.text_point(row, col)
    end = view.text_point(endrow, endcol)
    return sublime.Region(start, end)
  
  @staticmethod
  def trim_Region(view, region):
    new_region = sublime.Region(region.begin(), region.end())
    while(view.substr(new_region).startswith(" ") or view.substr(new_region).startswith("\n")):
      new_region.a = new_region.a + 1
    while(view.substr(new_region).endswith(" ") or view.substr(new_region).startswith("\n")):
      new_region.b = new_region.b - 1
    return new_region

  @staticmethod
  def selection_in_js_scope(view, point = -1, except_for = ""):
    try :

      sel_begin = view.sel()[0].begin() if point == -1 else point

      return view.match_selector(
        sel_begin,
        'source.js ' + except_for
      ) or view.match_selector(
        sel_begin,
        'source.js.embedded.html ' + except_for
      )

    except IndexError as e:
      return False   
  
  @staticmethod
  def replace_with_tab(view, region, pre="", after="", add_to_each_line_before="", add_to_each_line_after="") :
    lines = view.substr(region).split("\n")
    body = list()
    empty_line = 0
    for line in lines :
      if line.strip() == "" :
        empty_line = empty_line + 1
        if empty_line == 2 :
          empty_line = 1 # leave at least one empty line
          continue
      else :
        empty_line = 0
      line = "\t"+add_to_each_line_before+line+add_to_each_line_after
      body.append(line)
    if body[len(body)-1].strip() == "" :
      del body[len(body)-1]
    body = "\n".join(body)
    return pre+body+after

  @staticmethod
  def replace_without_tab(view, region, pre="", after="", add_to_each_line_before="", add_to_each_line_after="") :
    lines = view.substr(region).split("\n")
    body = list()
    empty_line = 0
    for line in lines :
      if line.strip() == "" :
        empty_line = empty_line + 1
        if empty_line == 2 :
          empty_line = 1 # leave at least one empty line
          continue
      else :
        empty_line = 0
      body.append(add_to_each_line_before+line+add_to_each_line_after)
    if body[len(body)-1].strip() == "" :
      del body[len(body)-1]
    body = "\n".join(body)
    return pre+body+after

  @staticmethod
  def get_whitespace_from_line_begin(view, region) :
    return " " * ( region.begin() - view.line(region).begin() )

  @staticmethod
  def add_whitespace_indentation(view, region, string, replace="\t", add_whitespace_end=True) :
    whitespace = Util.get_whitespace_from_line_begin(view, region)
    if replace == "\n" :
      lines = string.split("\n")
      lines = [whitespace+line for line in lines]
      lines[0] = lines[0].lstrip()
      string = "\n".join(lines)
      return string
    if add_whitespace_end :
      lines = string.split("\n")
      lines[len(lines)-1] = whitespace + lines[-1:][0]
    string = "\n".join(lines)
    string = re.sub("(["+replace+"]+)", whitespace+r"\1", string)
    return string

  @staticmethod
  def go_to_centered(view, row, col):
    while view.is_loading() :
      time.sleep(.1)
    point = view.text_point(row, col)
    view.sel().clear()
    view.sel().add(point)
    view.show_at_center(point)

  @staticmethod
  def wait_view(view, fun):
    while view.is_loading() :
      time.sleep(.1)
    fun()

  @staticmethod
  def move_content_to_parent_folder(path):
    for filename in os.listdir(path):
      shutil.move(os.path.join(path, filename), os.path.dirname(path)) 
    os.rmdir(path)

  @staticmethod
  def merge_dicts(*dict_args):
      result = {}
      for dictionary in dict_args:
          result.update(dictionary)
      return result

  @staticmethod
  def removeItemIfExists(arr, item):
    if item in arr: arr.remove(item)

  @staticmethod
  def getListItemIfExists(arr, item):
    if item in arr : 
      return item
    return None

  @staticmethod
  def delItemIfExists(obj, key):
    try :
      del obj[key]
    except KeyError as e:
      pass

  @staticmethod
  def getDictItemIfExists(obj, key):
    try :
      return obj[key]
    except KeyError as e:
      pass
    return None

  @staticmethod
  def create_and_show_panel(output_panel_name, window = None, syntax=""):
    window = sublime.active_window() if not window else window
    panel = window.create_output_panel(output_panel_name, False)
    panel.set_read_only(True)
    if syntax :
      panel.set_syntax_file(syntax)
    window.run_command("show_panel", {"panel": "output."+output_panel_name})
    return panel

  @staticmethod
  def execute(command, command_args, chdir="", wait_terminate=True, func_stdout=None, args_func_stdout=[]) :

    if sublime.platform() == 'windows':
      args = [command] + command_args
    else :
      command_args_list = list()
      for command_arg in command_args :
        command_args_list.append(shlex.quote(command_arg))
      command_args = " ".join(command_args_list)
      args = shlex.quote(command)+" "+command_args
    
    #print(args)

    if wait_terminate :

      env = os.environ.copy()
      env["PATH"] = env["PATH"] + javascriptCompletions.get("PATH")
      shell = None if sublime.platform() == 'windows' else '/bin/bash'

      with subprocess.Popen(args, shell=True, executable=shell, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=(None if not chdir else chdir)) as p:

        lines_output = []
        lines_error = []

        thread_output = Util.create_and_start_thread(Util._wrapper_func_stdout_listen_output, "", (p, None, [], lines_output))

        thread_error = Util.create_and_start_thread(Util._wrapper_func_stdout_listen_error, "", (p, None, [], lines_error))

        if thread_output:
          thread_output.join()

        if thread_error:
          thread_error.join()

        lines = "\n".join(lines_output) + "\n" + "\n".join(lines_error)

        return [True if p.wait() == 0 else False, lines]

    elif not wait_terminate and func_stdout :

      return Util.create_and_start_thread(Util._wrapper_func_stdout, "", (args, func_stdout, args_func_stdout, chdir))
  
  @staticmethod
  def _wrapper_func_stdout(args, func_stdout, args_func_stdout=[], chdir=""):

    env = os.environ.copy()
    env["PATH"] = env["PATH"] + javascriptCompletions.get("PATH")
    shell = None if sublime.platform() == 'windows' else '/bin/bash'

    with subprocess.Popen(args, shell=True, executable=shell, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, preexec_fn=os.setsid, cwd=(None if not chdir else chdir)) as p:

      func_stdout(None, p, *args_func_stdout)
      
      thread_output = Util.create_and_start_thread(Util._wrapper_func_stdout_listen_output, "", (p, func_stdout, args_func_stdout))

      thread_error = Util.create_and_start_thread(Util._wrapper_func_stdout_listen_error, "", (p, func_stdout, args_func_stdout))

      if thread_output:
        thread_output.join()
        
      if thread_error:
        thread_error.join()

      if p.wait() == 0:
        func_stdout("OUTPUT-SUCCESS", p, *args_func_stdout)
      else :
        func_stdout("OUTPUT-ERROR", p, *args_func_stdout)

      func_stdout("OUTPUT-DONE", p, *args_func_stdout)

  @staticmethod
  def _wrapper_func_stdout_listen_output(process, func_stdout=None, args_func_stdout=[], lines_output=[]):

    char = b""
    line = b""

    while True :
      char = process.stdout.read(1)
      if not char :
        break
      if not char.endswith(b'\n') :
        line = line + char
      else :
        line = line + char
        line = codecs.decode(line, "utf-8", "ignore").strip()
        line = re.sub(r'\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))', '', line)
        line = re.sub(r'[\n\r]', '\n', line)
        lines_output.append(line)
        line = line + ( b"\n" if type(line) is bytes else "\n" ) 
        if func_stdout :
          func_stdout(line, process, *args_func_stdout)
        line = b""
      char = b""
  
  @staticmethod
  def _wrapper_func_stdout_listen_error(process, func_stdout=None, args_func_stdout=[], lines_error=[]):

    char = b""
    line = b""

    while True :
      char = process.stderr.read(1)
      if not char :
        break
      if not char.endswith(b'\n') :
        line = line + char
      else :
        line = line + char
        line = codecs.decode(line, "utf-8", "ignore").strip()
        line = re.sub(r'\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))', '', line)
        line = re.sub(r'[\n\r]', '\n', line)
        lines_error.append(line)
        line = line + ( b"\n" if type(line) is bytes else "\n" ) 
        if func_stdout :
          func_stdout(line, process, *args_func_stdout)
        line = b""
      char = b""

  @staticmethod
  def nested_lookup(key, values, document, wild=False):
      """Lookup a key in a nested document, return a list of values"""
      return list(Util._nested_lookup(key, values, document, wild=wild))

  @staticmethod
  def _nested_lookup(key, values, document, wild=False):
      """Lookup a key in a nested document, yield a value"""
      if isinstance(document, list):
          for d in document:
              for result in Util._nested_lookup(key, values, d, wild=wild):
                  yield result

      if isinstance(document, dict):
          for k, v in document.items():
              if values and v in values and (key == k or (wild and key.lower() in k.lower())):
                  yield document
              elif not values and key == k or (wild and key.lower() in k.lower()):
                  yield document
              elif isinstance(v, dict):
                  for result in Util._nested_lookup(key, values, v, wild=wild):
                      yield result
              elif isinstance(v, list):
                  for d in v:
                      for result in Util._nested_lookup(key, values, d, wild=wild):
                          yield result
import time, os, re, threading, socket, traceback, sys, struct

class mySocketClient():
  def __init__(self, socket_name) :
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.socket_name = socket_name
    self.func_on_recv = None

  def connect(self, host, port):
    self.socket_name += "_"+host+":"+str(port)
    try:
      self.socket.connect((host, port))
      self.socket.setblocking(False)
      self.log('Client connected')
      Util.create_and_start_thread(target=self.on_recv)
    except socket.error as msg:
      self.log('Connection failed. Error : ' + str(sys.exc_info()))
      sys.exit()

  def on_recv(self):
    while True:
      time.sleep(.1)
      
      input_from_server_bytes = self.recv_data() # the number means how the response can be in bytes  
      if input_from_server_bytes is False :
        break
      if input_from_server_bytes :
        input_from_server = input_from_server_bytes.decode("utf8") # the return will be in bytes, so decode
        if self.func_on_recv :
          self.func_on_recv(input_from_server)

  def recv_data(self):
    try:
      size = self.socket.recv(struct.calcsize("<i"))
      if size :
        size = struct.unpack("<i", size)[0]
        data = b""
        while len(data) < size:
          try:
            msg = self.socket.recv(size - len(data))
            if not msg:
              return None
            data += msg
          except socket.error:
            pass
        return data
      else :
        return False
    except socket.error:
      pass
    except OSError as e:
      self.log(traceback.format_exc())
      return False

  def send_to_server(self, data) :
    self.socket.settimeout(1)
    try :
      data = struct.pack("<i", len(data)) + data.encode("utf-8")
      self.socket.sendall(data)
      return True
    except socket.timeout:
      self.log("Socket server dead. Closing connection...")
      self.close()
      return False
    except socket.error :
      self.log("Socket server dead. Closing connection...")
      self.close()
      return False

  def handle_recv(self, func):
    self.func_on_recv = func

  def get_socket(self):
    return self.socket

  def log(self, message) :
    print(self.socket_name + ": "+message)

  def close(self) :
    if self.socket :
      self.socket.close()
      self.socket = None

class mySocketServer():
  def __init__(self, socket_name, accept=False) :
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.clients = dict()
    self.socket_name = socket_name
    self.accept_only_one_client = accept
    self.func_on_client_connected = None
    self.func_on_client_disconnected = None
    self.func_on_recv = None
    self.log('Socket created')

  def bind(self, host, port):
    self.socket_name += "_"+host+":"+str(port)
    try:
      self.socket.bind((host, port))
      self.log('Socket bind complete')
    except socket.error as msg:
      self.log('Bind failed. Error : ' + traceback.format_exc())

  def listen(self, backlog=5) :
    self.socket.listen(backlog)
    self.log('Socket now listening')
    Util.create_and_start_thread(target=self.main_loop)

  def main_loop(self):
    while True:
      time.sleep(.1)

      try :
        conn, addr = self.socket.accept()   
        if len(self.clients) > 0 and self.accept_only_one_client :
          self.send_to(conn, addr, "server_accept_only_one_client")
          continue
        conn.setblocking(False)
        ip, port = str(addr[0]), str(addr[1])
        self.clients[ip+":"+str(port)] = dict()
        self.clients[ip+":"+str(port)]["socket"] = conn
        self.clients[ip+":"+str(port)]["addr"] = addr

        self.log('Accepting connection from ' + ip + ':' + port)

        if self.func_on_client_connected :
          self.func_on_client_connected(conn, addr, ip, port, self.clients[ip+":"+str(port)])

        try:
          Util.create_and_start_thread(target=self.on_recv, args=(conn, addr, ip, port))
        except:
          self.log(traceback.format_exc())
      except ConnectionAbortedError:
        self.log("Connection aborted")
        break

  def on_recv(self, conn, addr, ip, port):
    while True:
      time.sleep(.1)

      input_from_client_bytes = self.recv_data(conn)

      if input_from_client_bytes is False :

        self.delete_client(conn, addr)
        if self.func_on_client_disconnected :
          self.func_on_client_disconnected(conn, addr, ip, port)
        self.log('Connection ' + ip + ':' + port + " ended")
        break

      if input_from_client_bytes :

        # decode input and strip the end of line
        input_from_client = input_from_client_bytes.decode("utf8")

        if self.func_on_recv :
          self.func_on_recv(conn, addr, ip, port, input_from_client, self.clients[ip+":"+str(port)])

  def recv_data(self, conn):
    try:
      size = conn.recv(struct.calcsize("<i"))
      if size :
        size = struct.unpack("<i", size)[0]
        data = b""
        while len(data) < size:
          try:
            msg = conn.recv(size - len(data))
            if not msg:
              return None
            data += msg
          except socket.error as e:
            pass
        return data
      else :
        return False
    except socket.error as e:
      pass
    except OSError as e:
      self.log(traceback.format_exc())
      return False

  def send_to(self, conn, addr, data) :
    conn.settimeout(1)
    try:
      data = struct.pack("<i", len(data)) + data.encode("utf-8")
      return self.send_all_data_to(conn, addr, data)
    except socket.timeout:
      self.delete_client(conn, addr)
      self.log("Timed out "+str(addr[0])+":"+str(addr[1]))
      return False
    except OSError as e:
      self.delete_client(conn, addr)
      self.log(traceback.format_exc())
      return False

  def send_all_data_to(self, conn, addr, data):
    totalsent = 0
    data_size = len(data)
    while totalsent < data_size:
      sent = conn.sendto(data[totalsent:], addr)
      if sent == 0:
        self.delete_client(conn, addr)
        self.log(traceback.format_exc())
        return False
      totalsent = totalsent + sent
    return True

  def send_all_clients(self, data) :
    for key, value in self.clients.items() :
      self.send_to(value["socket"], value["addr"], data)

  def handle_recv(self, func):
    self.func_on_recv = func

  def handle_client_connection(self, func):
    self.func_on_client_connected = func

  def handle_client_disconnection(self, func):
    self.func_on_client_disconnected = func

  def get_socket(self):
    return self.socket

  def set_accept_only_one_client(accept):
    self.accept_only_one_client = accept

  def get_clients(self) :
    return self.clients

  def find_clients_by_field(self, field, field_value) :
    clients_found = list()
    for key, value in self.clients.items() :
      if field in value and value[field] == field_value :
        clients_found.append(value)
    return clients_found

  def get_first_client(self) :
    for client in self.clients :
      return client

  def delete_client(self, conn, addr) :
    try :
      del self.clients[str(addr[0])+":"+str(addr[1])]
    except KeyError:
      pass
    conn.close()

  def log(self, message) :
    print(self.socket_name + ": "+message)

  def close_if_not_clients(self) :
    if not self.clients:
      self.close()
      return True
    return False

  def close(self) :
    if self.socket :
      self.socket.close()
      self.socket = None


KEYMAP_COMMANDS = []
keymaps = Util.open_json(os.path.join(PACKAGE_PATH, 'Default.sublime-keymap'))
for keymap in keymaps:
  if keymap["command"] != "window_view_keypress":
    KEYMAP_COMMANDS += [keymap["command"]]

def sublime_executable_path():
  executable_path = sublime.executable_path()

  if sublime.platform() == 'osx':
    app_path = executable_path[:executable_path.rfind(".app/") + 5]
    executable_path = app_path + "Contents/SharedSupport/bin/subl"

  elif sublime.platform() == 'windows':
    executable_path = os.path.join(os.path.dirname(executable_path), "subl.exe")

  return executable_path

def subl(args):
  
  executable_path = sublime_executable_path()

  args_list = list()

  if sublime.platform() == 'windows' :
    args = [executable_path] + args
    for arg in args :
      args_list.append(json.dumps(arg))
    json.dumps(executable_path)
  else :
    for arg in args :
      args_list.append(shlex.quote(arg))
    shlex.quote(executable_path)
  
  args = executable_path + " " + " ".join(args_list)

  return subprocess.Popen(args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def overwrite_default_javascript_snippet():
  if not os.path.isdir(os.path.join(SUBLIME_PACKAGES_PATH, "JavaScript")) :
    os.mkdir(os.path.join(SUBLIME_PACKAGES_PATH, "JavaScript"))
  if not os.path.isdir(os.path.join(SUBLIME_PACKAGES_PATH, "JavaScript", "Snippets")) :
    os.mkdir(os.path.join(SUBLIME_PACKAGES_PATH, "JavaScript", "Snippets"))
  for file_name in os.listdir(os.path.join(PACKAGE_PATH, "JavaScript-overwrite-default-snippet")) :
    if file_name.endswith(".sublime-snippet") and os.path.isfile(os.path.join(PACKAGE_PATH, "JavaScript-overwrite-default-snippet", file_name)) :
      shutil.copy(os.path.join(PACKAGE_PATH, "JavaScript-overwrite-default-snippet", file_name), os.path.join(SUBLIME_PACKAGES_PATH, "JavaScript", "Snippets", file_name))

class show_javascript_enhancements_versionCommand(sublime_plugin.WindowCommand):
  def run(self):
    if sublime.ok_cancel_dialog("JavaScript Enhancements plugin version: "+PLUGIN_VERSION, "Copy"):
      sublime.set_clipboard(PLUGIN_VERSION)

class startPlugin():
  def init(self):
 
    node_modules_path = os.path.join(PACKAGE_PATH, "node_modules")
    npm = NPM()

    if os.path.exists(node_modules_path) and not os.path.exists(os.path.join(node_modules_path, ".bin")):
      if sublime.platform() == "windows":
        os.system("taskkill /f /im flow.exe")
      shutil.rmtree(node_modules_path)

    if not os.path.exists(node_modules_path):
      animation_npm_installer = AnimationLoader(["[=     ]", "[ =    ]", "[   =  ]", "[    = ]", "[     =]", "[    = ]", "[   =  ]", "[ =    ]"], 0.067, "JavaScript Enhancements - installing npm dependencies ")
      interval_animation = RepeatedTimer(animation_npm_installer.sec, animation_npm_installer.animate)

      result = npm.install_all()
      if result[0]: 
        animation_npm_installer.on_complete()
        interval_animation.stop()
        sublime.active_window().status_message("JavaScript Enhancements - npm dependencies installed correctly.")
      else:
        animation_npm_installer.on_complete()
        interval_animation.stop()
        print(result)
        if os.path.exists(node_modules_path):
          shutil.rmtree(node_modules_path)
        sublime.error_message("Error during installation: can't install npm dependencies for JavaScript Enhancements plugin.\n\nThe error COULD be caused by the npm permission access (EACCES error), so in this case you need to repair/install node.js and npm in a way that doesn't require \"sudo\" command.\n\nFor example you could use a Node Version Manager, such as \"nvm\" or \"nodenv\".\n\nTry to run \"npm install\" inside the package of this plugin to see what you get.")
        return
    
    sublime.set_timeout_async(lambda: overwrite_default_javascript_snippet())

    window = sublime.active_window()
    view = window.active_view()

    sublime.set_timeout_async(lambda: show_flow_errorsViewEventListener(view).on_activated_async())

mainPlugin = startPlugin()

import sublime, sublime_plugin
import os, tempfile, queue
from collections import namedtuple

flowCLIRequirements = namedtuple('flowCLIRequirements', [
    'filename', 'project_root', 'contents', 'cursor_pos', 'row', 'col', 'row_offset'
])

FLOW_DEFAULT_CONFIG_PATH = os.path.join(PACKAGE_PATH, "flow")

def flow_parse_cli_dependencies(view, **kwargs):
  filename = view.file_name()
  
  project_settings = get_project_settings()
  if project_settings:
    project_root = project_settings["project_dir_name"]
  else:
    contextual_keys = sublime.active_window().extract_variables()
    folder_path = contextual_keys.get("folder")
    if folder_path and os.path.isdir(folder_path) and os.path.isfile(os.path.join(folder_path, '.flowconfig')) :  
      project_root = folder_path
    else :
      project_root = FLOW_DEFAULT_CONFIG_PATH

  cursor_pos = 0
  if kwargs.get('cursor_pos') :
    cursor_pos = kwargs.get('cursor_pos')
  else :
    if len(view.sel()) > 0 :
      cursor_pos = view.sel()[0].begin()
    
  row, col = view.rowcol(cursor_pos)

  if kwargs.get('check_all_source_js_embedded'):
    embedded_regions = view.find_by_selector("source.js.embedded.html")
    if not embedded_regions :
      return flowCLIRequirements(
        filename=None,
        project_root=None,
        contents="",
        cursor_pos=None,
        row=None, col=None,
        row_offset=0
      )
    flowCLIRequirements_list = list()
    for region in embedded_regions:
      current_contents = view.substr(region)
      row_scope, col_scope = view.rowcol(region.begin())
      row_offset = row_scope
      row_scope = row - row_scope

      flowCLIRequirements_list.append(flowCLIRequirements(
        filename=filename,
        project_root=project_root,
        contents=current_contents,
        cursor_pos=cursor_pos,
        row=row, col=col,
        row_offset=row_offset
      ))
    return flowCLIRequirements_list
  else :
    scope_region = None
    if view.match_selector(
        cursor_pos,
        'source.js'
    ) and view.substr(sublime.Region(0, view.size()) ) == "" :
      scope_region = sublime.Region(0, 0)
    else :
      scope = view.scope_name(cursor_pos)
      result = Util.get_region_scope_first_match(view, scope, sublime.Region(cursor_pos, cursor_pos), "source.js")
      if not result:
        result = Util.get_region_scope_first_match(view, scope, sublime.Region(cursor_pos, cursor_pos), "source.js.embedded.html")
        if not result:
          return flowCLIRequirements(
            filename=None,
            project_root=None,
            contents="",
            cursor_pos=None,
            row=None, col=None,
            row_offset=0
          )
      scope_region = result["region"]
    current_contents = view.substr(scope_region)
    row_scope, col_scope = view.rowcol(scope_region.begin())
    row_offset = row_scope
    row_scope = row - row_scope
    """
    current_contents = view.substr(
      sublime.Region(0, view.size())
    )
    """
    
    if kwargs.get('add_magic_token'):
      current_lines = current_contents.splitlines()
      try :
        current_line = current_lines[row_scope]
      except IndexError as e:
        return flowCLIRequirements(
            filename=None,
            project_root=None,
            contents="",
            cursor_pos=None,
            row=None, col=None,
            row_offset=0
          )
      tokenized_line = ""
      if not kwargs.get('not_add_last_part_tokenized_line') :
        tokenized_line = current_line[0:col] + 'AUTO332' + current_line[col:-1]
      else :
        tokenized_line = current_line[0:col] + 'AUTO332'
      current_lines[row_scope] = tokenized_line
      current_contents = '\n'.join(current_lines)

    return flowCLIRequirements(
      filename=filename,
      project_root=project_root,
      contents=current_contents,
      cursor_pos=cursor_pos,
      row=row, col=col,
      row_offset=row_offset
    )


import sublime, sublime_plugin
import os, shlex, collections

PROJECT_SETTINGS_FOLDER_NAME = ".je-project-settings"

def open_project_folder(project):
  
  if not is_project_open(project) :
    subl(["--project", project])

def is_project_open(project): 

  project_folder_to_find = os.path.dirname(project)

  windows = sublime.windows()

  for window in windows :

    project_file_name = sublime.active_window().project_file_name()

    if project_file_name :
      project_folder = os.path.dirname(project_file_name)

      return True if project_folder == project_folder_to_find else False

    else :
      # try to look at window.folders()
      folders = window.folders()   
      if len(folders) > 0:

        project_folder = folders[0]

        return True if project_folder == project_folder_to_find else False

  return False
  
def is_javascript_project():
  project_file_name = sublime.active_window().project_file_name()
  project_dir_name = ""
  if project_file_name :
    project_dir_name = os.path.dirname(project_file_name)
    settings_dir_name = os.path.join(project_dir_name, PROJECT_SETTINGS_FOLDER_NAME)
    return os.path.isdir(settings_dir_name)
  else :
    # try to look at window.folders()
    folders = sublime.active_window().folders()   
    if len(folders) > 0:
      folders = folders[0]
      settings_dir_name = os.path.join(folders, PROJECT_SETTINGS_FOLDER_NAME)
      return os.path.isdir(settings_dir_name)
  return False

def is_type_javascript_project(type):
  settings = get_project_settings()
  return True if settings and os.path.exists(os.path.join(settings["settings_dir_name"], type+"_settings.json")) else False

def is_project_view(view) :
  settings = get_project_settings()
  if settings :
    # added view.file_name() == None because of new files without a name
    return ( view.file_name() and view.file_name().startswith(settings["project_dir_name"]) ) or view.file_name() == None
  return False

def get_project_settings(project_dir_name = ""):

  project_settings = dict()

  project_file_name = sublime.active_window().project_file_name() if not project_dir_name else ""
  settings_dir_name = ""

  if not project_dir_name :

    if project_file_name :
      project_dir_name = os.path.dirname(project_file_name)
    else :
      # try to look at window.folders()
      folders = sublime.active_window().folders()
      if len(folders) > 0:
        project_dir_name = folders[0]

  if not project_dir_name :
    return dict()

  if project_file_name :
    settings_dir_name = os.path.join(project_dir_name, PROJECT_SETTINGS_FOLDER_NAME)
    if not os.path.isdir(settings_dir_name) :
      return dict()
  else :
    for file in os.listdir(project_dir_name) :
      if file.endswith(".sublime-project") :
        project_file_name = os.path.join(project_dir_name, file)
        break
    settings_dir_name = os.path.join(project_dir_name, PROJECT_SETTINGS_FOLDER_NAME)
    if not os.path.isdir(settings_dir_name) :
      return dict()
        
  project_settings["project_file_name"] = project_file_name
  project_settings["project_dir_name"] = project_dir_name
  project_settings["settings_dir_name"] = settings_dir_name
  settings_file = ["project_details.json", "project_settings.json"]
  for setting_file in os.listdir(project_settings["settings_dir_name"]) :
    with open(os.path.join(settings_dir_name, setting_file), encoding="utf-8") as file :
      key = os.path.splitext(setting_file)[0]
      project_settings[key] = json.loads(file.read(), encoding="utf-8", object_pairs_hook=collections.OrderedDict)
  
  return project_settings

def save_project_setting(setting_file, data):
  settings = get_project_settings()
  if settings :
    with open(os.path.join(settings["settings_dir_name"], setting_file), 'w+', encoding="utf-8") as file :
      file.write(json.dumps(data, indent=2))

import sublime, sublime_plugin
import os

class enable_menu_project_typeEventListener(sublime_plugin.EventListener):
  project_type = ""
  path = ""
  path_disabled = ""

  def on_activated(self, view):
    if self.project_type and self.path and self.path_disabled:
      if is_type_javascript_project(self.project_type) :
        if os.path.isfile(self.path_disabled):
          os.rename(self.path_disabled, self.path)
      else :
        if os.path.isfile(self.path):
          os.rename(self.path, self.path_disabled)
    elif self.path and self.path_disabled:
      if is_javascript_project() :
        if os.path.isfile(self.path_disabled):
          os.rename(self.path_disabled, self.path)
      else :
        if os.path.isfile(self.path):
          os.rename(self.path, self.path_disabled)

  def on_new(self, view):
    self.on_activated(view)

  def on_load(self, view):
    self.on_activated(view)


import sublime, sublime_plugin
import shlex, json, os

class manage_cliCommand(sublime_plugin.WindowCommand):
  
  custom_name = ""
  cli = ""
  path_cli = ""
  settings_name = ""
  placeholders = {}
  settings = None
  command = []
  working_directory = ""
  isNode = False
  isNpm = False
  isBinPath = False
  alsoNonProject = False

  def run(self, **kwargs):

    self.settings = get_project_settings()

    if self.settings:

      if not self.settings_name:
        self.working_directory = self.settings["project_dir_name"]
      else:
        self.working_directory =  self.settings[self.settings_name]["working_directory"]

      if self.isNode:
        self.path_cli = self.settings["project_settings"]["node_js_custom_path"] or javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
      elif self.isNpm:
        if self.settings["project_settings"]["use_yarn"]:
          self.path_cli = self.settings["project_settings"]["yarn_custom_path"] or javascriptCompletions.get("yarn_custom_path") or YARN_EXEC
        else:
          self.path_cli = self.settings["project_settings"]["npm_custom_path"] or javascriptCompletions.get("npm_custom_path") or NPM_EXEC
      else:
        self.path_cli = self.settings[self.settings_name]["cli_custom_path"] if self.settings[self.settings_name]["cli_custom_path"] else ( javascriptCompletions.get(self.custom_name+"_custom_path") if javascriptCompletions.get(self.custom_name+"_custom_path") else self.cli )    

        if sublime.platform() != "windows" and (self.settings["project_settings"]["node_js_custom_path"] or javascriptCompletions.get("node_js_custom_path")):
          if os.path.isabs(self.path_cli) :
            self.command = [shlex.quote(self.path_cli)]
          else:
            self.command = ["$(which "+shlex.quote(self.path_cli)+")"]
          self.path_cli = self.settings["project_settings"]["node_js_custom_path"] or javascriptCompletions.get("node_js_custom_path")

      if kwargs.get("command"):
        if not self.command:
          self.command = kwargs.get("command")
        else:
          self.command += kwargs.get("command")

      self.prepare_command(**kwargs)

    elif self.alsoNonProject:

      self.working_directory = os.path.expanduser("~")

      if self.isNode:
        self.path_cli = javascriptCompletions.get("node_js_custom_path") or NODE_JS_EXEC
      elif self.isNpm:
        if self.settings["project_settings"]["use_yarn"]:
          self.path_cli = javascriptCompletions.get("yarn_custom_path") or YARN_EXEC
        else:
          self.path_cli = javascriptCompletions.get("npm_custom_path") or NPM_EXEC
      else:
        self.path_cli = javascriptCompletions.get(self.custom_name+"_custom_path") if javascriptCompletions.get(self.custom_name+"_custom_path") else self.cli

        if sublime.platform() != "windows" and javascriptCompletions.get("node_js_custom_path"):
          if os.path.isabs(self.path_cli) :
            self.command = [shlex.quote(self.path_cli)]
          else:
            self.command = ["$(which "+shlex.quote(self.path_cli)+")"]
          self.path_cli = javascriptCompletions.get("node_js_custom_path")

      if kwargs.get("command"):
        if not self.command:
          self.command = kwargs.get("command")
        else:
          self.command += kwargs.get("command")

      self.prepare_command(**kwargs)

    else :
      sublime.error_message("Error: can't get project settings")


  def prepare_command(self):
    pass

  def _run(self):

    if self.isNode and self.isBinPath:
      self.command[0] = shlex.quote(os.path.join(NODE_MODULES_BIN_PATH, self.command[0])) if sublime.platform() != "windows" else os.path.join(NODE_MODULES_BIN_PATH, self.command[0]+".cmd")

    self.working_directory = shlex.quote(self.working_directory) if sublime.platform() != "windows" else self.working_directory
    self.path_cli = shlex.quote(self.path_cli) if sublime.platform() != "windows" else self.path_cli

    if sublime.platform() != "windows": 
      views = self.window.views()
      view_with_term = None
      for view in views:
        if view.name() == "JavaScript Enhancements Terminal (bash)":
          view_with_term = view

      if view_with_term:
        self.window.focus_view(view_with_term)
        self.window.run_command("terminal_view_send_string", args={"string": "cd "+self.working_directory+"\n"})
      else :
        self.window.run_command("set_layout", args={"cells": [[0, 0, 1, 1], [0, 1, 1, 2]], "cols": [0.0, 1.0], "rows": [0.0, 0.7, 1.0]})
        self.window.focus_group(1)
        view = self.window.new_file() 
        args = {"cmd": "/bin/bash -l", "title": "JavaScript Enhancements Terminal (bash)", "cwd": self.working_directory, "syntax": None, "keep_open": False} 
        view.run_command('terminal_view_activate', args=args)

      # stop the current process with SIGINT and call the command
      sublime.set_timeout_async(lambda: self.window.run_command("terminal_view_send_string", args={"string": "\x03"}) or
        self.window.run_command("terminal_view_send_string", args={"string": self.path_cli+" "+(" ".join(self.command))+"\n"}), 500)

    else:
      terminal = Terminal(cwd=self.working_directory, title="JavaScript Enhancements Terminal (bash)")
      terminal.run([self.path_cli]+self.command)

  def substitute_placeholders(self, variable):
    
    if isinstance(variable, list) :

      for index in range(len(variable)):
        for key, placeholder in self.placeholders.items():
          variable[index] = variable[index].replace(key, placeholder)

      return variable

    elif isinstance(variable, str) :

      for key, placeholder in self.placeholders.items():
        variable = variable.replace(key, placeholder)
        
      return variable

import sublime, sublime_plugin
import subprocess, shutil, traceback, os, json, shlex, collections

class create_new_projectCommand(sublime_plugin.WindowCommand):
  project_type = None

  def run(self, **kwargs):

    self.window.show_quick_panel(PROJECT_TYPE_SUPPORTED, self.project_type_selected)

  def project_type_selected(self, index):

    if index == -1:
      return
      
    self.project_type = PROJECT_TYPE_SUPPORTED[index]

    # Testing WindowView()
    # self.WindowView = WindowView()
    # self.WindowView.addTitle(text="Create JavaScript Project")
    # self.WindowView.add(text="\n")
    # self.WindowView.add(text="Project Path: ", region_id="test")
    # self.WindowView.addInput(value=os.path.expanduser("~")+os.path.sep, region_id="project_path")
    # self.WindowView.add(text="\n\n")
    # Hook.apply(self.project_type+"_create_window_view", self.WindowView)
    # self.WindowView.add(text="\n\n")
    # self.WindowView.addButton(text="CREATE", scope="javascriptenhancements.button_ok")
    # self.WindowView.add(text="        ")
    # self.WindowView.addButton(text="CANCEL", scope="javascriptenhancements.button_cancel")
    # self.WindowView.add(text=" \n")
    # self.WindowView.addEventListener("drag_select", "click.javascriptenhancements.button_ok", lambda view: self.project_path_on_done(self.WindowView.getInput("project_path")))
    # self.WindowView.addEventListener("drag_select", "click.javascriptenhancements.button_cancel", lambda view: self.WindowView.close())

    self.window.show_input_panel("Project Path:", os.path.expanduser("~")+os.path.sep, self.project_path_on_done, None, None)

  def project_path_on_done(self, path):

    path = path.strip()

    if os.path.isdir(os.path.join(path, PROJECT_SETTINGS_FOLDER_NAME)):
      sublime.error_message("Can't create the project. There is already another project in "+path+".")
      return

    if not os.path.isdir(path):
      if sublime.ok_cancel_dialog("The path \""+path+"\" doesn't exists.\n\nDo you want create it?", "Yes"):
        os.makedirs(path)
      else:
        return

    Hook.apply("create_new_project", path)
    Hook.apply(self.project_type+"_create_new_project", path)

    os.makedirs(os.path.join(path, PROJECT_SETTINGS_FOLDER_NAME))

    PROJECT_SETTINGS_FOLDER_PATH = os.path.join(path, PROJECT_SETTINGS_FOLDER_NAME)

    default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "create_new_project", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
    
    sublime_project_file_path = os.path.join(path, os.path.basename(path)+".sublime-project")
    package_json_file_path = os.path.join(path, "package.json")
    flowconfig_file_path = os.path.join(path, ".flowconfig")
    bookmarks_path = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "bookmarks.json")
    project_details_file = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "project_details.json")
    project_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "project_settings.json")

    if not os.path.exists(sublime_project_file_path) :
      with open(sublime_project_file_path, 'w+', encoding="utf-8") as file:
        file.write(json.dumps(default_config["sublime_project"], indent=2))

    if ( self.project_type == "empty" or self.project_type == "cordova" ) and not os.path.exists(package_json_file_path) :
      with open(package_json_file_path, 'w+', encoding="utf-8") as file:
        file.write(json.dumps(default_config["package_json"], indent=2))

    with open(bookmarks_path, 'w+', encoding="utf-8") as file:
      file.write(json.dumps(default_config["bookmarks"], indent=2))
    with open(project_details_file, 'w+', encoding="utf-8") as file:
      file.write(json.dumps(default_config["project_details"], indent=2))
    with open(project_settings, 'w+', encoding="utf-8") as file:
      file.write(json.dumps(default_config["project_settings"], indent=2))

    if not os.path.exists(flowconfig_file_path) :
      node = NodeJS(check_local=True)
      result = node.execute("flow", ["init"], is_from_bin=True, chdir=path)
      if not result[0]:
        sublime.error_message("Can't initialize flow.")
      else:
        with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
          content = file.read()
          content = content.replace("[ignore]", """[ignore]
<PROJECT_ROOT>/"""+PROJECT_SETTINGS_FOLDER_NAME+"""/.*""")
          file.seek(0)
          file.truncate()
          file.write(content)

    Hook.apply(self.project_type+"_after_create_new_project", path, "create_new_project")
    Hook.apply("after_create_new_project", path, "create_new_project")

    if self.project_type == "empty":
      open_project_folder(get_project_settings(path)["project_file_name"])

class add_javascript_project_typeCommand(sublime_plugin.WindowCommand):
  project_type = None
  settings = None

  def run(self, **kwargs):
    self.settings = get_project_settings()
    if self.settings:
      self.window.show_quick_panel(PROJECT_TYPE_SUPPORTED, self.project_type_selected)
    else:
      sublime.error_message("No JavaScript project found.")

  def project_type_selected(self, index):

    if index == -1:
      return

    self.project_type = PROJECT_TYPE_SUPPORTED[index]
    self.window.show_input_panel("Working Directory:", self.settings["project_dir_name"]+os.path.sep, self.working_directory_on_done, None, None)

  def working_directory_on_done(self, working_directory):

    working_directory = shlex.quote( working_directory.strip() )

    if not os.path.isdir(working_directory):
      os.makedirs(working_directory)

    Hook.apply("add_javascript_project_type", working_directory, "add_project_type")
    Hook.apply(self.project_type+"_add_javascript_project_type", working_directory, "add_project_type")

  def is_visible(self):
    return is_javascript_project()

  def is_enabled(self):
    return is_javascript_project()

class add_javascript_project_type_configurationCommand(sublime_plugin.WindowCommand):
  project_type = None
  settings = None

  def run(self, *args):
    self.settings = get_project_settings()
    if self.settings:
      self.window.show_quick_panel(list( set(PROJECT_TYPE_SUPPORTED) - set(["yeoman"]) ), self.project_type_selected)
    else:
      sublime.error_message("No JavaScript project found.")

  def project_type_selected(self, index):

    if index == -1:
      return

    self.project_type = list( set(PROJECT_TYPE_SUPPORTED) - set(["yeoman"]) )[index]
    self.window.show_input_panel("Working directory:", self.settings["project_dir_name"]+os.path.sep, self.working_directory_on_done, None, None)

  def working_directory_on_done(self, working_directory):

    working_directory = shlex.quote( working_directory.strip() )

    if not os.path.isdir(working_directory):
      os.makedirs(working_directory)

    Hook.apply("add_javascript_project_configuration", working_directory, "add_project_configuration")
    Hook.apply(self.project_type+"_add_javascript_project_configuration", working_directory, "add_project_configuration")

  def is_visible(self):
    return is_javascript_project()

  def is_enabled(self):
    return is_javascript_project()


import sublime, sublime_plugin
import os, time, signal

class close_flowEventListener(sublime_plugin.EventListener):

  def on_pre_close(self, view) :

    node = NodeJS()

    if not sublime.windows() :

      sublime.status_message("flow server stopping")
      sublime.set_timeout_async(lambda: node.execute("flow", ["stop"], is_from_bin=True, chdir=os.path.join(PACKAGE_PATH, "flow")))

    settings = get_project_settings()

    if settings and view.window() and len(view.window().views()) == 1 :
      settings = get_project_settings()
      sublime.status_message("flow server stopping")

      flow_cli = "flow"
      is_from_bin = True
      chdir = settings["project_dir_name"]
      use_node = True
      bin_path = ""

      if settings["project_settings"]["flow_cli_custom_path"]:
        flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
        bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
        is_from_bin = False
        use_node = False
    
      sublime.set_timeout_async(lambda: node.execute(flow_cli, ["stop"], is_from_bin=is_from_bin, chdir=chdir, bin_path=bin_path, use_node=use_node))


class enable_menu_npmEventListener(enable_menu_project_typeEventListener):
  path = os.path.join(PROJECT_FOLDER, "npm", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "npm", "Main_disabled.sublime-menu")

  def on_activated(self, view):
    super(enable_menu_npmEventListener, self).on_activated(view)

    default_value = [
      {
        "caption": "Tools",
        "id": "tools",
        "children": [
          {
            "caption": "Npm/Yarn Scripts",
            "id": "npm_scripts",
            "children":[]
          }
        ]
      }
    ]

    if os.path.isfile(self.path) :
      with open(self.path, 'r+') as menu:
        content = menu.read()
        menu.seek(0)
        menu.write(json.dumps(default_value))
        menu.truncate()
        json_data = json.loads(content)
        npm_scripts = None
        for item in json_data :
          if item["id"] == "tools" :
            for item2 in item["children"] :
              if item2["id"] == "npm_scripts" :
                item2["children"] = []
                npm_scripts = item2["children"]
            break
        if npm_scripts == None :
          return 
        try:
          npm = NPM(check_local=True)
          package_json = npm.getPackageJson()
          if package_json and "scripts" in package_json and len(package_json["scripts"].keys()) > 0 :
            for script in package_json["scripts"].keys():
              npm_scripts.append({
                "caption": script,
                "command": "manage_npm",
                "args": {
                  "command": ["run", script]
                }
              })
            menu.seek(0)
            menu.write(json.dumps(json_data))
            menu.truncate()
        except Exception as e:
          print(traceback.format_exc())
          menu.seek(0)
          menu.write(json.dumps(default_value))
          menu.truncate()

    if os.path.isfile(self.path_disabled) :
      with open(self.path_disabled, 'w+') as menu:
        menu.write(json.dumps(default_value))

class manage_npmCommand(manage_cliCommand):

  isNpm = True

  def prepare_command(self, **kwargs):

    self._run()

  def is_enabled(self):
    settings = get_project_settings()
    return True if settings and os.path.isfile( os.path.join(settings["project_dir_name"], "package.json") ) else False

  def is_visible(self):
    settings = get_project_settings()
    return True if settings and os.path.isfile( os.path.join(settings["project_dir_name"], "package.json") ) else False


import shlex, shutil, json

class enable_menu_build_flowEventListener(enable_menu_project_typeEventListener):
  path = os.path.join(PROJECT_FOLDER, "flow", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "flow", "Main_disabled.sublime-menu")

class build_flowCommand(manage_cliCommand):

  isNode = True
  isBinPath = True

  def prepare_command(self, **kwargs):

    # dest_folder = self.settings["project_settings"]["build_flow"]["destination_folder"]

    # if os.path.isabs(dest_folder):
    #   shutil.rmtree(dest_folder)
    # elif os.path.exists(os.path.join(self.settings["project_dir_name"], dest_folder)):
    #   shutil.rmtree(os.path.join(self.settings["project_dir_name"], dest_folder))

    self.placeholders[":source_folders"] = " ".join(self.settings["project_settings"]["build_flow"]["source_folders"])
    self.placeholders[":destination_folder"] = self.settings["project_settings"]["build_flow"]["destination_folder"]
    self.command += self.settings["project_settings"]["build_flow"]["options"]
    self.command = self.substitute_placeholders(self.command)

    if self.settings["project_settings"]["flow_remove_types_custom_path"]:
      self.isBinPath = False
      self.command[0] = shlex.quote(self.settings["project_settings"]["flow_remove_types_custom_path"])

    self._run()

  def _run(self):
    super(build_flowCommand, self)._run()

  def is_enabled(self) :
    settings = get_project_settings()
    if settings and len(settings["project_settings"]["build_flow"]["source_folders"]) > 0 and settings["project_settings"]["build_flow"]["destination_folder"] :
      return True
    return False

class build_flow_on_save(sublime_plugin.EventListener):

  def on_post_save_async(self, view):
    settings = get_project_settings()
    if Util.selection_in_js_scope(view) and settings and settings["project_settings"]["build_flow"]["on_save"] and len(settings["project_settings"]["build_flow"]["source_folders"]) > 0 and settings["project_settings"]["build_flow"]["destination_folder"] :
      view.window().run_command("build_flow", args={"command": ["flow-remove-types", ":source_folders", "--out-dir", ":destination_folder"]})

class add_flow_definitionCommand(sublime_plugin.WindowCommand):

  flow_typed_searched_items = []

  def run(self, **kwargs):

    self.window.show_input_panel("Definition to search", "", lambda package_name: sublime.set_timeout_async(lambda: self.search(package_name)), None, None)

  def search(self, package_name):

    self.window.status_message("Searching for '" + package_name + "' definitions...")
    node = NodeJS(check_local=True)
    result = node.execute("flow-typed", command_args=["search", package_name], is_from_bin=True)

    if result[0]:
      lines = result[1].encode('ascii', errors='ignore').decode("utf-8").strip().split("\n")
      linesNotDecoded = result[1].strip().split("\n")
      found_definations_flag = False
      for i in range(0, len(lines)):
        line = lines[i].strip()
        lineNotDecoded = linesNotDecoded[i].strip()

        if found_definations_flag and line:
   
          item = lineNotDecoded.split(b'\xe2\x94\x82'.decode("utf-8"))
          for j in range(0, len(item)):
            item[j] = item[j].encode('ascii', errors='ignore').decode("utf-8").strip()

          self.flow_typed_searched_items += [[item[0] + " " + item[1], "Flow version supported: " + item[2]]]

        elif line.startswith("Name") and line.endswith("Flow Version"):
          found_definations_flag = True

      if len(self.flow_typed_searched_items) > 0:
        self.window.show_quick_panel(self.flow_typed_searched_items, lambda index: sublime.set_timeout_async(lambda: self.install_definition(index)), sublime.KEEP_OPEN_ON_FOCUS_LOST)
      else:
        self.window.status_message("No definitions found, sorry!")

  def install_definition(self, index):

    if index == -1:
      return
      
    settings = get_project_settings()
    if settings: 
      package = self.flow_typed_searched_items[index][0].rsplit(' ', 1)
      package_name = package[0].strip()
      version = package[1].strip()[1:]
      flow_bin_version = ""

      self.window.status_message("Installing definition '" + package_name + "@" + version + "'...")

      if settings["project_settings"]["flow_cli_custom_path"]:
        result = Util.execute(settings["project_settings"]["flow_cli_custom_path"], command_args=["version", "--json"], chdir=settings["project_dir_name"])
        if result[0]:
          flow_bin_version = json.loads(result[1])["semver"]

      flow_cli = "flow"
      is_from_bin = True
      chdir = settings["project_dir_name"]
      use_node = True
      bin_path = ""

      if settings["project_settings"]["flow_cli_custom_path"]:
        flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
        bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
        is_from_bin = False
        use_node = False

      node = NodeJS(check_local=True)
      if not flow_bin_version:
        result = node.execute(flow_cli, command_args=["version", "--json"], is_from_bin=is_from_bin, chdir=chdir, bin_path=bin_path, use_node=use_node)
        if result[0]:
          flow_bin_version = json.loads(result[1])["semver"]

      if flow_bin_version:
        # example: flow-typed install -f 0.62.0 express@4.x.x
        result = node.execute("flow-typed", command_args=["install", "-f", flow_bin_version, package_name+"@"+version], is_from_bin=True, chdir=chdir)

        if result[0]:
          self.window.status_message("Defintion '" + package_name + "@" + version + "' installed successfully!")
        else:
          print(result)
          self.window.status_message("Can't install '" + package_name + "@" + version + "' definition! Something went wrong, sorry!")

      else:
        print(result)
        self.window.status_message("Can't install '" + package_name + "@" + version + "' definition! Something went wrong, sorry!")

    else:
      sublime.error_message("Error: can't get project settings")

  def is_enabled(self):
    return is_javascript_project()

  def is_visible(self):
    return is_javascript_project()


import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def cordova_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Cordova CLI custom path", "cordova", lambda cordova_custom_path: cordova_prepare_project(project_path, cordova_custom_path) if type == "create_new_project" or type == "add_project_type" else add_cordova_settings(project_path, cordova_custom_path), None, None)

def add_cordova_settings(working_directory, cordova_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]

  flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
    content = file.read()
    content = content.replace("[ignore]", """[ignore]
<PROJECT_ROOT>/platforms/.*
<PROJECT_ROOT>/hooks/.*
<PROJECT_ROOT>/plugins/.*
<PROJECT_ROOT>/res/.*""")
    file.seek(0)
    file.truncate()
    file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "cordova", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = cordova_custom_path

  cordova_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "cordova_settings.json")

  with open(cordova_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def cordova_prepare_project(project_path, cordova_custom_path):

  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(cordova_custom_path), "create", "myApp", "com.example.hello", "HelloWorld", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([cordova_custom_path, "create", "myApp", "com.example.hello", "HelloWorld", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp"])
    if open_project:
      terminal.run(open_project)

  add_cordova_settings(project_path, cordova_custom_path)

Hook.add("cordova_after_create_new_project", cordova_ask_custom_path)
Hook.add("cordova_add_javascript_project_configuration", cordova_ask_custom_path)
Hook.add("cordova_add_javascript_project_type", cordova_ask_custom_path)

class enable_menu_cordovaEventListener(enable_menu_project_typeEventListener):
  project_type = "cordova"
  path = os.path.join(PROJECT_FOLDER, "cordova", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "cordova", "Main_disabled.sublime-menu")

class cordova_cliCommand(manage_cliCommand):

  cli = "cordova"
  custom_name = "cordova"
  settings_name = "cordova_settings"

  def prepare_command(self, **kwargs):

    if ":platform" in self.command:
      self.window.show_input_panel("Platform:", "", self.platform_on_done, None, None)
    else :
      self._run()

  def platform_on_done(self, platform):
    self.placeholders[":platform"] = shlex.quote(platform.strip())
    self.command = self.substitute_placeholders(self.command)
    self._run()

  def _run(self):
    try:
      self.command = {
        'run': lambda : self.command + self.settings["cordova_settings"]["platform_run_options"][self.command[2].replace('--', '')][self.command[1]],
        'compile': lambda : self.command + self.settings["cordova_settings"]["platform_compile_options"][self.command[2].replace('--', '')][self.command[1]],
        'build': lambda : self.command + self.settings["cordova_settings"]["platform_build_options"][self.command[2].replace('--', '')][self.command[1]],
        'serve': lambda : self.command + [self.settings["cordova_settings"]["serve_port"]]
      }[self.command[0]]()
    except KeyError as err:
      pass
    except Exception as err:
      print(traceback.format_exc())
      pass

    super(cordova_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def ionicv1_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Ionic v1 CLI custom path", "ionic", lambda ionicv1_custom_path: ionicv1_prepare_project(project_path, ionicv1_custom_path) if type == "create_new_project" or type == "add_project_type" else add_ionicv1_settings(project_path, ionicv1_custom_path), None, None)

def add_ionicv1_settings(working_directory, ionicv1_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
    content = file.read()
    content = content.replace("[ignore]", """[ignore]
<PROJECT_ROOT>/platforms/.*
<PROJECT_ROOT>/hooks/.*
<PROJECT_ROOT>/plugins/.*
<PROJECT_ROOT>/resources/.*""")
    file.seek(0)
    file.truncate()
    file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "ionicv1", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = ionicv1_custom_path

  ionicv1_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "ionicv1_settings.json")

  with open(ionicv1_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def ionicv1_prepare_project(project_path, ionicv1_custom_path):
  
  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(ionicv1_custom_path), "start", "myApp", "blank", "--type", "ionic1", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([ionicv1_custom_path, "start", "myApp", "blank", "--type", "ionic1", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp"])
    if open_project:
      terminal.run(open_project)

  add_ionicv1_settings(project_path, ionicv1_custom_path)

Hook.add("ionicv1_after_create_new_project", ionicv1_ask_custom_path)
Hook.add("ionicv1_add_javascript_project_configuration", ionicv1_ask_custom_path)
Hook.add("ionicv1_add_javascript_project_type", ionicv1_ask_custom_path)

class enable_menu_ionicv1EventListener(enable_menu_project_typeEventListener):
  project_type = "ionicv1"
  path = os.path.join(PROJECT_FOLDER, "ionicv1", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "ionicv1", "Main_disabled.sublime-menu")

class ionicv1_cliCommand(manage_cliCommand):

  cli = "ionic"
  custom_name = "ionicv1"
  settings_name = "ionicv1_settings"

  def prepare_command(self, **kwargs):

    if ":platform" in self.command:
      self.window.show_input_panel("Platform:", "", self.platform_on_done, None, None)
    else :
      self._run()

  def platform_on_done(self, platform):
    self.placeholders[":platform"] = shlex.quote(platform.strip())
    self.command = self.substitute_placeholders(self.command)
    self._run()

  def _run(self):
    try:
      self.command = {
        'run': lambda : self.command + self.settings["ionicv1_settings"]["platform_run_options"][self.command[2].replace('--', '')][self.command[1]],
        'compile': lambda : self.command + self.settings["ionicv1_settings"]["platform_compile_options"][self.command[2].replace('--', '')][self.command[1]],
        'build': lambda : self.command + self.settings["ionicv1_settings"]["platform_build_options"][self.command[2].replace('--', '')][self.command[1]],
        'prepare': lambda : self.command + self.settings["ionicv2_settings"]["platform_prepare_options"][self.command[1]],
        'serve': lambda : self.command + self.settings["ionicv1_settings"]["serve_options"]
      }[self.command[0]]()
    except KeyError as err:
      pass
    except Exception as err:
      print(traceback.format_exc())
      pass

    super(ionicv1_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def ionicv2_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Ionic v2 CLI custom path", "ionic", lambda ionicv2_custom_path: ionicv2_prepare_project(project_path, ionicv2_custom_path) if type == "create_new_project" or type == "add_project_type" else add_ionicv2_settings(project_path, ionicv2_custom_path), None, None)

def add_ionicv2_settings(working_directory, ionicv2_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
    content = file.read()
    content = content.replace("[ignore]", """[ignore]
<PROJECT_ROOT>/platforms/.*
<PROJECT_ROOT>/hooks/.*
<PROJECT_ROOT>/plugins/.*
<PROJECT_ROOT>/resources/.*
<PROJECT_ROOT>/.sourcemaps/.*""")
    file.seek(0)
    file.truncate()
    file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "ionicv2", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = ionicv2_custom_path

  ionicv2_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "ionicv2_settings.json")

  with open(ionicv2_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def ionicv2_prepare_project(project_path, ionicv2_custom_path):
  
  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(ionicv2_custom_path), "start", "myApp", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([ionicv2_custom_path, "start", "myApp", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp"])
    if open_project:
      terminal.run(open_project)

  add_ionicv2_settings(project_path, ionicv2_custom_path)

Hook.add("ionicv2_after_create_new_project", ionicv2_ask_custom_path)
Hook.add("ionicv2_add_javascript_project_configuration", ionicv2_ask_custom_path)
Hook.add("ionicv2_add_javascript_project_type", ionicv2_ask_custom_path)

class enable_menu_ionicv2EventListener(enable_menu_project_typeEventListener):
  project_type = "ionicv2"
  path = os.path.join(PROJECT_FOLDER, "ionicv2", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "ionicv2", "Main_disabled.sublime-menu")

class ionicv2_cliCommand(manage_cliCommand):

  cli = "ionic"
  custom_name = "ionicv2"
  settings_name = "ionicv2_settings"

  def prepare_command(self, **kwargs):

    if ":platform" in self.command:
      self.window.show_input_panel("Platform:", "", self.platform_on_done, None, None)
    elif ":integration_id" in self.command:
      self.window.show_input_panel("Integration id:", "", self.integration_id_on_done, None, None)
    else :
      self._run()

  def platform_on_done(self, platform):
    self.placeholders[":platform"] = shlex.quote(platform.strip())
    self.command = self.substitute_placeholders(self.command)
    self._run()

  def integration_id_on_done(self, integration_id):
    self.placeholders[":integration_id"] = shlex.quote(integration_id.strip())
    self.command = self.substitute_placeholders(self.command)
    self._run()

  def _run(self):
    try:
      if self.command[0] == "cordova":
        self.command = {
          'run': lambda : self.command + self.settings["ionicv2_settings"]["platform_run_options"][self.command[3].replace('--', '')][self.command[2]],
          'compile': lambda : self.command + self.settings["ionicv2_settings"]["platform_compile_options"][self.command[3].replace('--', '')][self.command[2]],
          'build': lambda : self.command + self.settings["ionicv2_settings"]["platform_build_options"][self.command[3].replace('--', '')][self.command[2]],
          'emulate': lambda : self.command + self.settings["ionicv2_settings"]["platform_emulate_options"][self.command[3].replace('--', '')][self.command[2]],
          'prepare': lambda : self.command + self.settings["ionicv2_settings"]["platform_prepare_options"][self.command[2]]
        }[self.command[1]]()
      else:
        self.command = {
          'serve': lambda : self.command + self.settings["ionicv2_settings"]["serve_options"]
        }[self.command[0]]()
    except KeyError as err:
      pass
    except Exception as err:
      print(traceback.format_exc())
      pass

    super(ionicv2_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def angularv1_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Yeoman CLI custom path", "yo", lambda angularv1_custom_path: angularv1_prepare_project(project_path, angularv1_custom_path) if type == "create_new_project" or type == "add_project_type" else add_angularv1_settings(project_path, angularv1_custom_path), None, None)

def add_angularv1_settings(working_directory, angularv1_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  # flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  # with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
  #   content = file.read()
  #   content = content.replace("[ignore]", """[ignore]""")
  #   file.seek(0)
  #   file.truncate()
  #   file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "angularv1", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = angularv1_custom_path

  angularv1_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "angularv1_settings.json")

  with open(angularv1_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def angularv1_prepare_project(project_path, angularv1_custom_path):
  
  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(angularv1_custom_path), "angular"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([angularv1_custom_path, "angular"])
    if open_project:
      terminal.run(open_project)

  add_angularv1_settings(project_path, angularv1_custom_path)

Hook.add("angularv1_after_create_new_project", angularv1_ask_custom_path)
Hook.add("angularv1_add_javascript_project_configuration", angularv1_ask_custom_path)
Hook.add("angularv1_add_javascript_project_type", angularv1_ask_custom_path)

class enable_menu_angularv1EventListener(enable_menu_project_typeEventListener):
  project_type = "angularv1"
  path = os.path.join(PROJECT_FOLDER, "angularv1", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "angularv1", "Main_disabled.sublime-menu")

class angularv1_cliCommand(manage_cliCommand):

  cli = "yo"
  custom_name = "angularv1"
  settings_name = "angularv1_settings"

  def prepare_command(self, **kwargs):

    if ":name" in self.command:
      sublime.active_window().show_input_panel( (self.command[0].replace("angular:", ""))+" name:", "", self.name_on_done, None, None )
    else :
      self._run()

  def name_on_done(self, name):
    self.placeholders[":name"] = shlex.quote(name.strip())
    self.command = self.substitute_placeholders(self.command)
    self._run()

  def _run(self):
    # try:
    #   self.command = {
    #     'serve': lambda : self.command + self.settings["angularv1_settings"]
    #   }[self.command[0]]()
    # except KeyError as err:
    #   pass
    # except Exception as err:
    #   print(traceback.format_exc())
    #   pass

    super(angularv1_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def angularv2_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("@angular/cli custom path", "ng", lambda angularv2_custom_path: angularv2_prepare_project(project_path, angularv2_custom_path) if type == "create_new_project" or type == "add_project_type" else add_angularv2_settings(project_path, angularv2_custom_path), None, None)

def add_angularv2_settings(working_directory, angularv2_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  # flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  # with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
  #   content = file.read()
  #   content = content.replace("[ignore]", """[ignore]""")
  #   file.seek(0)
  #   file.truncate()
  #   file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "angularv2", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = angularv2_custom_path

  angularv2_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "angularv2_settings.json")

  with open(angularv2_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def angularv2_prepare_project(project_path, angularv2_custom_path):
  
  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(angularv2_custom_path), "new", "myApp", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([angularv2_custom_path, "new", "myApp", "HelloWorld", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp"])
    if open_project:
      terminal.run(open_project)

  add_angularv2_settings(project_path, angularv2_custom_path)

Hook.add("angularv2_after_create_new_project", angularv2_ask_custom_path)
Hook.add("angularv2_add_javascript_project_configuration", angularv2_ask_custom_path)
Hook.add("angularv2_add_javascript_project_type", angularv2_ask_custom_path)

class enable_menu_angularv2EventListener(enable_menu_project_typeEventListener):
  project_type = "angularv2"
  path = os.path.join(PROJECT_FOLDER, "angularv2", "Main.sublime-menu")
  path_disabled = os.path.join(PROJECT_FOLDER, "angularv2", "Main_disabled.sublime-menu")

class angularv2_cliCommand(manage_cliCommand):

  cli = "ng"
  custom_name = "angularv2"
  settings_name = "angularv2_settings"

  def prepare_command(self, **kwargs):

    if ":name_and_options" in self.command:
      sublime.active_window().show_input_panel( self.command[0] + " " + self.command[1] + " name and options:", "", self.name_and_options_on_done, None, None )
    else :
      self._run()

  def name_and_options_on_done(self, name_and_options):
    self.placeholders[":name_and_options"] = name_and_options.strip()
    self.command = self.substitute_placeholders(self.command)
    self._run()

  def _run(self):

    try:
      self.command = {
        'build': lambda : self.command + self.settings["angularv2_settings"]["platform_run_options"][self.command[2].replace('--', '')],
        'serve': lambda : self.command + self.settings["angularv2_settings"]["serve_options"],
        'lint': lambda : self.command + self.settings["angularv2_settings"]["lint_options"],
        'test': lambda : self.command + self.settings["angularv2_settings"]["test_options"],
        'e2e': lambda : self.command + self.settings["angularv2_settings"]["e2e_options"],
        'eject': lambda : self.command + self.settings["angularv2_settings"]["eject_options"],
        'xi18n': lambda : self.command + self.settings["angularv2_settings"]["xi18n_options"]
      }[self.command[0]]()
    except KeyError as err:
      pass
    except Exception as err:
      print(traceback.format_exc())
      pass
 
    super(angularv2_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def react_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Create-react-app CLI custom path", "create-react-app", lambda react_custom_path: react_prepare_project(project_path, react_custom_path) if type == "create_new_project" or type == "add_project_type" else add_react_settings(project_path, react_custom_path), None, None)

def add_react_settings(working_directory, react_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  # flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  # with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
  #   content = file.read()
  #   content = content.replace("[ignore]", """[ignore]""")
  #   file.seek(0)
  #   file.truncate()
  #   file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "react", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = react_custom_path

  react_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "react_settings.json")

  with open(react_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def react_prepare_project(project_path, react_custom_path):

  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(react_custom_path), "myApp", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([react_custom_path, "myApp", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp"])
    if open_project:
      terminal.run(open_project)

  add_react_settings(project_path, react_custom_path)

Hook.add("react_after_create_new_project", react_ask_custom_path)
Hook.add("react_add_javascript_project_configuration", react_ask_custom_path)
Hook.add("react_add_javascript_project_type", react_ask_custom_path)

# class enable_menu_reactEventListener(enable_menu_project_typeEventListener):
#   project_type = "react"
#   path = os.path.join(PROJECT_FOLDER, "react", "Main.sublime-menu")
#   path_disabled = os.path.join(PROJECT_FOLDER, "react", "Main_disabled.sublime-menu")

# class react_cliCommand(manage_cliCommand):

#   cli = "create-react-app"
#   custom_name = "react"
#   settings_name = "react_settings"

#   def prepare_command(self, **kwargs):

#     self._run()

#   def _run(self):

#     super(react_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def react_native_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Create-react-native-app CLI custom path", "create-react-native-app", lambda react_native_custom_path: react_native_prepare_project(project_path, react_native_custom_path) if type == "create_new_project" or type == "add_project_type" else add_react_native_settings(project_path, react_native_custom_path), None, None)

def add_react_native_settings(working_directory, react_native_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  # flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  # with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
  #   content = file.read()
  #   content = content.replace("[ignore]", """[ignore]""")
  #   file.seek(0)
  #   file.truncate()
  #   file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "react-native", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = react_native_custom_path

  react_native_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "react_native_settings.json")

  with open(react_native_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def react_native_prepare_project(project_path, react_native_custom_path):

  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(react_native_custom_path), "myApp", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([react_native_custom_path, "myApp", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp"])
    if open_project:
      terminal.run(open_project)

  add_react_native_settings(project_path, react_native_custom_path)

Hook.add("react-native_after_create_new_project", react_native_ask_custom_path)
Hook.add("react-native_add_javascript_project_configuration", react_native_ask_custom_path)
Hook.add("react-native_add_javascript_project_type", react_native_ask_custom_path)

# class enable_menu_react_nativeEventListener(enable_menu_project_typeEventListener):
#   project_type = "react-native"
#   path = os.path.join(PROJECT_FOLDER, "react_native", "Main.sublime-menu")
#   path_disabled = os.path.join(PROJECT_FOLDER, "react_native", "Main_disabled.sublime-menu")

# class react_native_cliCommand(manage_cliCommand):

#   cli = "create-react-native-app"
#   custom_name = "react_native"
#   settings_name = "react_native_settings"

#   def prepare_command(self, **kwargs):

#     self._run()

#   def _run(self):

#     super(react_native_cliCommand, self)._run()



import sublime, sublime_plugin
import os, webbrowser, shlex, json

def yeoman_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Yeoman CLI custom path", "yo", lambda yeoman_custom_path: yeoman_prepare_project(project_path, yeoman_custom_path), None, None)

def yeoman_prepare_project(project_path, yeoman_custom_path):

  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(yeoman_custom_path)] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([yeoman_custom_path])
    if open_project:
      terminal.run(open_project)

Hook.add("yeoman_after_create_new_project", yeoman_ask_custom_path)
Hook.add("yeoman_add_javascript_project_type", yeoman_ask_custom_path)

import sublime, sublime_plugin
import os, webbrowser, shlex, json, collections

def express_ask_custom_path(project_path, type):
    sublime.active_window().show_input_panel("Express generator CLI custom path", "express", lambda express_custom_path: express_prepare_project(project_path, express_custom_path) if type == "create_new_project" or type == "add_project_type" else add_express_settings(project_path, express_custom_path), None, None)

def add_express_settings(working_directory, express_custom_path):
  project_path = working_directory
  settings = get_project_settings()
  if settings :
    project_path = settings["project_dir_name"]
    
  # flowconfig_file_path = os.path.join(project_path, ".flowconfig")
  # with open(flowconfig_file_path, 'r+', encoding="utf-8") as file:
  #   content = file.read()
  #   content = content.replace("[ignore]", """[ignore]""")
  #   file.seek(0)
  #   file.truncate()
  #   file.write(content)

  PROJECT_SETTINGS_FOLDER_PATH = os.path.join(project_path, PROJECT_SETTINGS_FOLDER_NAME)

  default_config = json.loads(open(os.path.join(PROJECT_FOLDER, "express", "default_config.json")).read(), object_pairs_hook=collections.OrderedDict)
  default_config["working_directory"] = working_directory
  default_config["cli_custom_path"] = express_custom_path

  express_settings = os.path.join(PROJECT_SETTINGS_FOLDER_PATH, "express_settings.json")

  with open(express_settings, 'w+') as file:
    file.write(json.dumps(default_config, indent=2))

def express_prepare_project(project_path, express_custom_path):

  terminal = Terminal(cwd=project_path)
  
  if sublime.platform() != "windows": 
    open_project = ["&&", shlex.quote(sublime_executable_path()), shlex.quote(get_project_settings(project_path)["project_file_name"])] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([shlex.quote(express_custom_path), "myApp", ";", "mv", "./myApp/{.[!.],}*", "./", ";", "rm", "-rf", "myApp", ";", NPM().cli_path, "install"] + open_project)
  else:
    open_project = [sublime_executable_path(), get_project_settings(project_path)["project_file_name"], "&&", "exit"] if not is_project_open(get_project_settings(project_path)["project_file_name"]) else []
    terminal.run([express_custom_path, "myApp", "&", os.path.join(WINDOWS_BATCH_FOLDER, "move_all.bat"), "myApp", ".", "&", "rd", "/s", "/q", "myApp", "&", NPM().cli_path, "install"])
    if open_project:
      terminal.run(open_project)

  add_express_settings(project_path, express_custom_path)

Hook.add("express_after_create_new_project", express_ask_custom_path)
Hook.add("express_add_javascript_project_configuration", express_ask_custom_path)
Hook.add("express_add_javascript_project_type", express_ask_custom_path)

# class enable_menu_expressEventListener(enable_menu_project_typeEventListener):
#   project_type = "express"
#   path = os.path.join(PROJECT_FOLDER, "express", "Main.sublime-menu")
#   path_disabled = os.path.join(PROJECT_FOLDER, "express", "Main_disabled.sublime-menu")

# class express_cliCommand(manage_cliCommand):

#   cli = "express"
#   custom_name = "express"
#   settings_name = "express_settings"

#   def prepare_command(self, **kwargs):

#     self._run()

#   def _run(self):

#     super(express_cliCommand, self)._run()




import sublime, sublime_plugin
import json, os, re, webbrowser, cgi, threading, shutil
from distutils.version import LooseVersion

import sublime, sublime_plugin
import shlex, json, os
from os.path import expanduser

class Terminal():

  def __init__(self, cmd="", title="", cwd="", syntax=None, keep_open=False, window=None):

    if sublime.platform() != "windows": 
      self.cmd = cmd or "/bin/bash -l"
    else :
      self.cmd = cmd or "cmd.exe"

    self.title = title or "Terminal"
    self.cwd = cwd or os.path.expanduser("~")
    self.syntax = syntax
    self.keep_open = keep_open
    self.window = window or sublime.active_window()

  def run(self, cmd_args):
    if sublime.platform() != "windows": 
      view = self.window.new_file() 
      view.run_command('terminal_view_activate', args={"cmd": self.cmd, "title": self.title, "cwd": self.cwd, "syntax": self.syntax, "keep_open": self.keep_open} )
      self.window.run_command("terminal_view_send_string", args={"string": " ".join(cmd_args) + "\n"})
    else:
      subprocess.Popen( [self.cmd] + 
        ( ["-NoExit", "-Command"] if self.cmd.startswith("powershell") else ["/K"] )
        + ( ["$Host.UI.RawUI.WindowTitle", "=", self.title] if self.cmd.startswith("powershell") else ["title", self.title] ) 
        + ( [";", "CD", self.cwd] if self.cmd.startswith("powershell") else ["&&", "CD", self.cwd] ) 
        + ( [";"] if self.cmd.startswith("powershell") else ["&&"] ) 
        + cmd_args 
      )


import sublime, sublime_plugin

class WindowView():

  def __init__(self, title="WindowView", window=None, view=None):
    self.view = ( sublime.active_window().new_file() if not window else window.new_file() ) if not view else view
    self.view.set_name(title)
    self.view.set_read_only(True)
    self.view.set_scratch(True)
    self.view.settings().set("javascript_enhancements_window_view", True)
    self.view.settings().set("gutter", False)
    self.view.settings().set("highlight_line", False)
    self.view.settings().set("auto_complete_commit_on_tab", False)
    self.view.settings().set("draw_centered", False)
    self.view.settings().set("word_wrap", False)
    self.view.settings().set("auto_complete", False)
    self.view.settings().set("draw_white_space", "none")
    self.view.settings().set("draw_indent_guides", False)
    self.view.settings().set("wide_caret", True)
    self.view.settings().set("rulers", "blink")
    self.view.settings().add_on_change('color_scheme', lambda: self.setColorScheme())
    self.events = dict()
    self.region_ids = []
    self.region_input_ids = []

    Hook.add("javascript_enhancements_window_view_close_"+str(self.view.id()), self.destroy)

  def __del__(self):
    Hook.removeAllHook("javascript_enhancements_window_view_close_"+str(self.view.id()))
    for event in self.events.keys():
      for eventRegionKey in self.events[event].keys():
        for callback in self.events[event][eventRegionKey].keys():
          self.removeEventListener(event, eventRegionKey, self.events[event][eventRegionKey][callback])

  def add(self, text, key="", scope="", icon="", flags=sublime.HIDDEN, region_id="", padding=0, display_block=False, insert_point=None, replace_points=[]):

    if region_id in self.region_ids:
      raise Exception("Error: ID "+region_id+" already used.")

    space = (" "*int(padding))
    text = space+text+space

    self.view.set_read_only(False)

    if insert_point:

      self.view.run_command("insert_text_view", args={"text": text, "key": key, "scope": scope, "icon": icon, "flags": flags, "region_id": region_id, "point": insert_point})
      if display_block:
        self.view.run_command("insert_text_view", args={"text": "\n", "key": "", "scope": "", "icon": "", "flags": sublime.HIDDEN, "point": insert_point+len(text)})

    elif replace_points:

      self.view.run_command("replace_region_view", args={"text": text, "key": key, "scope": scope, "icon": icon, "flags": flags, "region_id": region_id, "start": replace_points[0], "end": replace_points[1]})
    
    else:

      self.view.run_command("append_text_view", args={"text": text, "key": key, "scope": scope, "icon": icon, "flags": flags, "region_id": region_id})
      if display_block:
        self.view.run_command("append_text_view", args={"text": "\n", "key": "", "scope": "", "icon": "", "flags": sublime.HIDDEN})

    self.view.set_read_only(True)
    if region_id:
      self.region_ids.append(region_id)

  def addTitle(self, text, key="", scope="javascriptenhancements.title", icon="", flags=sublime.DRAW_EMPTY | sublime.DRAW_NO_OUTLINE, region_id="", padding=2, display_block=True, insert_point=None, replace_points=[]):
    space_padding = (" "*int(padding))
    space_row = (" "*len(text))+(" "*int(padding)*2)
    text = space_row+"\n"+space_padding+text+space_padding+"\n"+space_row+" "
    self.add(text, key=key, scope=scope, icon=icon, flags=flags, region_id=region_id, padding=0, display_block=display_block, insert_point=insert_point, replace_points=replace_points)

  def addSubTitle(self, text, key="", scope="javascriptenhancements.subtitle", icon="", flags=sublime.DRAW_EMPTY | sublime.DRAW_NO_OUTLINE, region_id="", padding=1, display_block=True, insert_point=None, replace_points=[]):
    self.add(text, key=key, scope=scope, icon=icon, flags=flags, region_id=region_id, padding=padding, display_block=display_block, insert_point=insert_point, replace_points=replace_points)

  def addButton(self, text, scope, key="click", icon="", flags=sublime.DRAW_EMPTY | sublime.DRAW_NO_OUTLINE, region_id="", padding=1, display_block=False, insert_point=None, replace_points=[]):
    self.add(text, key=key, scope=scope, icon=icon, flags=flags, region_id=region_id, padding=padding, display_block=display_block, insert_point=insert_point, replace_points=replace_points)

  def addInput(self, value=" ", key="input", scope="javascriptenhancements.input", icon="", flags=sublime.DRAW_EMPTY | sublime.DRAW_NO_OUTLINE, region_id="", padding=1, display_block=False, insert_point=None, replace_points=[]):

    if not region_id:
      raise Exception("Error: ID isn't setted.")

    if region_id in self.region_input_ids:
      raise Exception("Error: ID "+region_id+" already used.")

    self.add(value, key=key, scope=scope, icon=icon, flags=flags, region_id=region_id, padding=padding, display_block=display_block, insert_point=insert_point, replace_points=replace_points)
    self.region_input_ids.append(region_id)

  def getInput(self, region_input_id):
    region = self.view.get_regions(region_input_id)
    if region:
      region = region[0]
      return self.view.substr(region)[1:-1]
    return None

  def getInputs(self):
    inputs = dict()
    for region_input_id in self.region_input_ids:
      inputs[region_id] = self.getInput(region_input_id)
    return inputs

  def replaceById(self, replace_region_id, text, key="", scope="", icon="", flags=sublime.HIDDEN, region_id="", padding=0, display_block=False, insert_point=None, replace_points=[]):

    region = self.view.get_regions(replace_region_id)
    if region:
      region = region[0]
    else:
      return

    self.removeById(replace_region_id)

    self.add(text, key=key, scope=scope, icon=icon, flags=flags, region_id=region_id, padding=padding, display_block=display_block, insert_point=insert_point, replace_points=[region.begin(), region.end()])

  def removeById(self, region_id):
    self.view.erase_regions(region_id)

    if region_id in self.region_ids:
      self.region_ids.remove(region_id)

    if region_id in self.region_input_ids:
      self.region_input_ids.remove(region_id)

  def addEventListener(self, event, region_key, callback):
    if not event in self.events:
      self.events[event] = dict()

    if not region_key in self.events[event]:
      self.events[event][region_key] = dict()

    eventCallback = lambda view, cmd_args: callback(self.view) if self.canCallback(view, cmd_args, region_key) else None
    self.events[event][region_key][callback] = eventCallback

    Hook.add(event, eventCallback)

  def removeEventListener(self, event, region_key, callback):

    if not event in self.events:
      return 

    if not region_key in self.events[event]:
      return 

    if not callback in self.events[event][region_key]:
      return 

    eventCallback = self.events[event][region_key][callback]

    Hook.removeHook(event, eventCallback)
    del self.events[event][region_key][callback]

  def canCallback(self, view, cmd_args, region_key):
    if not view:
      return False
    if view.id() != self.view.id():
      return False

    point = view.window_to_text((cmd_args.get("event").get("x"), cmd_args.get("event").get("y"))) if "event" in cmd_args and "x" in cmd_args.get("event") else self.view.sel()[0]

    for region in self.view.get_regions(region_key):
      if region.contains(point):
        return True

    return False

  def getView(self):
    return self.view

  def setColorScheme(self):
    color_scheme = "Packages/JavaScript Enhancements/JavaScript Enhancements.tmTheme"
    if self.view.settings().get('color_scheme') != color_scheme:
      self.view.settings().set('color_scheme', color_scheme)

  def close(self):
    self.view.close()
    self.destroy()

  def destroy(self, *args, **kwargs):
    self.__del__()

class insertTextViewCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    point = args.get("point")
    view.insert(edit, point, args.get("text"))
    region = sublime.Region(point, len(args.get("text")))
    if "key" in args:
      scope = args.get("scope") if "scope" in args else ""
      scope_dot = "." + scope if scope else ""
      icon = args.get("icon") if "icon" in args else ""
      flags = args.get("flags") if "flags" in args else sublime.HIDDEN
      key = args.get("key") + scope_dot
      regions = [region] + view.get_regions(args.get("key") + scope_dot)

      view.add_regions(key, regions, scope, icon, flags)

      if "region_id" in args and args.get("region_id"):
        view.add_regions(args.get("region_id"), [region], scope, icon, flags)

class replaceRegionViewCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    view.erase(edit, sublime.Region(args.get("start"), args.get("end")))
    view.insert(edit, args.get("start"), args.get("text"))
    region = sublime.Region(args.get("start"), args.get("start")+len(args.get("text")))
    if "key" in args:
      scope = args.get("scope") if "scope" in args else ""
      scope_dot = "." + scope if scope else ""
      icon = args.get("icon") if "icon" in args else ""
      flags = args.get("flags") if "flags" in args else sublime.HIDDEN
      key = args.get("key") + scope_dot
      regions = [region] + view.get_regions(args.get("key") + scope_dot)

      view.add_regions(key, regions, scope, icon, flags)

      if "region_id" in args and args.get("region_id"):
        view.add_regions(args.get("region_id"), [region], scope, icon, flags)

class replaceTextViewCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    region = sublime.Region(args.get("start"), args.get("end"))
    view.replace(edit, region, args.get("text"))
    if "key" in args:
      scope = args.get("scope") if "scope" in args else ""
      scope_dot = "." + scope if scope else ""
      icon = args.get("icon") if "icon" in args else ""
      flags = args.get("flags") if "flags" in args else sublime.HIDDEN
      key = args.get("key") + scope_dot
      regions = [region] + view.get_regions(args.get("key") + scope_dot)

      view.add_regions(key, regions, scope, icon, flags)

      if "region_id" in args and args.get("region_id"):
        view.add_regions(args.get("region_id"), [region], scope, icon, flags)

class appendTextViewCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    point = view.size()
    view.insert(edit, point, args.get("text"))
    region = sublime.Region(point, view.size())
    if "key" in args:
      scope = args.get("scope") if "scope" in args else ""
      scope_dot = "." + scope if scope else ""
      icon = args.get("icon") if "icon" in args else ""
      flags = args.get("flags") if "flags" in args else sublime.HIDDEN
      key = args.get("key") + scope_dot
      regions = [region] + view.get_regions(args.get("key") + scope_dot)

      view.add_regions(key, regions, scope, icon, flags)

      if "region_id" in args and args.get("region_id"):
        view.add_regions(args.get("region_id"), [region], scope, icon, flags)

class windowViewKeypressCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view

    if view.settings().get("javascript_enhancements_window_view"):
      key = args.get("key")

      if key == "tab" or key =="shift+tab":
        input_regions = view.get_regions("input.javascriptenhancements.input")
        for index in range(0, len(input_regions)):
          region = input_regions[index]
          if region.contains(view.sel()[0]):
            view.sel().clear()
            next_region = None
            if key == "tab":
              next_region = input_regions[index + 1] if index < len(input_regions) - 1 else input_regions[0]
            else:
              next_region = input_regions[index - 1] if index - 1 >= 0 else input_regions[-1]
            view.sel().add(next_region.begin()+1)
            return

        if len(input_regions) > 0:
          view.sel().clear()
          view.sel().add(input_regions[0].begin()+1)

      if key == "ctrl+alt+a":
        input_regions = view.get_regions("input.javascriptenhancements.input")
        for region in input_regions:
          if region.contains(view.sel()[0]):   
            view.sel().clear()
            view.sel().add(sublime.Region(region.begin()+1, region.end()-1))

class windowViewEventListener(sublime_plugin.EventListener):

  def on_modified_async(self, view):
    if view.settings().get("javascript_enhancements_window_view"):

      for region in view.get_regions("input.javascriptenhancements.input"):

        # this order is important!
        
        if region.contains(view.sel()[0]) and view.substr(region)[0] != " ":
          view.set_read_only(False)
          char = view.substr(region)[0]
          view.run_command("insert_text_view", args={"text": " ", "point": region.begin()+1})
          view.run_command("replace_text_view", args={"text": " ", "start": region.begin(), "end": region.begin()+1})
          view.run_command("replace_text_view", args={"text": char, "start": region.begin()+1, "end": region.begin()+2})
          view.set_read_only(True)
          view.sel().clear()
          view.sel().add(region.begin()+1)

        elif region.contains(view.sel()[0]) and view.substr(region)[-1] != " ":
          view.set_read_only(False)
          char = view.substr(region)[-1]
          view.run_command("insert_text_view", args={"text": " ", "point": region.end()-1})
          view.run_command("replace_text_view", args={"text": " ", "start": region.end(), "end": region.end()+1})
          view.run_command("replace_text_view", args={"text": char, "start": region.end()-1, "end": region.end()})
          view.set_read_only(True)
          view.sel().clear()
          view.sel().add(region.end())

        elif region.contains(view.sel()[0]) and region.size() == 2:
          view.set_read_only(False)
          view.run_command("insert_text_view", args={"text": " ", "point": region.begin()+1})
          view.set_read_only(True)
          view.sel().clear()
          view.sel().add(region.begin()+1)
          break 

    return

  def on_selection_modified_async(self, view):
    if view.settings().get("javascript_enhancements_window_view"):

      for region in view.get_regions("input.javascriptenhancements.input"):
        if view.sel()[0].begin() >= region.begin() + 1 and view.sel()[0].end() <= region.end() - 1:
          view.set_read_only(False)
          return
        elif view.sel()[0].begin() == view.sel()[0].end():
          if view.sel()[0].begin() == region.begin():
            view.sel().clear()
            view.sel().add(region.begin()+1)
            return
          elif view.sel()[0].end() == region.end() :
            view.sel().clear()
            view.sel().add(region.end()-1)
            return

      view.set_read_only(True)

  def on_text_command(self, view, command_name, args):
    if view.settings().get("javascript_enhancements_window_view"):
      Hook.apply(command_name, view, args)

  def on_close(self, view):
    if view.settings().get("javascript_enhancements_window_view"):
      Hook.apply("javascript_enhancements_window_view_close_"+str(view.id()))


import sublime, sublime_plugin

class navigate_regionsCommand():

  region_key = ""

  def run(self, edit, **args) :
    
    view = self.view

    regions = view.get_regions(self.region_key)
    if not regions:
      return
      
    move_type = args.get("type")

    if move_type == "next" :

      r_next = self.find_next(regions)
      if r_next != None :
        row, col = view.rowcol(r_next.begin())

        Util.go_to_centered(view, row, col)

    elif move_type == "previous" :

      r_prev = self.find_prev(regions)
      if r_prev != None :
        row, col = view.rowcol(r_prev.begin())

        Util.go_to_centered(view, row, col)

  def find_next(self, regions):
    view = self.view

    sel = view.sel()[0]

    for region in regions :
      if region.begin() > sel.begin() :
        return region

    if(len(regions) > 0) :
      return regions[0]

    return None

  def find_prev(self, regions):
    view = self.view

    sel = view.sel()[0]

    previous_regions = []
    for region in regions :
      if region.begin() < sel.begin() :
        previous_regions.append(region)

    if not previous_regions and len(regions) > 0:
      previous_regions.append(regions[len(regions)-1])

    return previous_regions[len(previous_regions)-1] if len(previous_regions) > 0 else None


import sublime, sublime_plugin

class wait_modified_asyncViewEventListener():
  last_change = time.time()
  waiting = False
  prefix_thread_name = ""
  wait_time = 1
  modified = False

  def on_modified_async(self, *args, **kwargs) :
    self.last_change = time.time()
    if not self.prefix_thread_name :
      raise Exception("No prefix_thread_name to wait_modified_asyncViewEventListener")
    Util.create_and_start_thread(self.on_modified_async_with_thread, self.prefix_thread_name+"_"+str(self.view.id()), args=args, kwargs=kwargs)

  def wait(self):
    if time.time() - self.last_change <= self.wait_time:
      if not self.waiting:
        self.waiting = True
      else :
        return
      sublime.set_timeout(self.wait_time)
      self.waiting = False

  def on_modified_async_with_thread(self, *args, **kwargs):
    return


import sublime, sublime_plugin

class enableKeymap(sublime_plugin.EventListener):

  def on_text_command(self, view, command_name, args):

    if command_name in KEYMAP_COMMANDS and not javascriptCompletions.get("enable_keymap"):
      return ("noop", {})

import sublime, sublime_plugin

class surround_withCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    selections = view.sel()
    case = args.get("case")
    if case == "if_else_statement" :
      if len(selections) != 2 :
        return

      sel_1 = Util.trim_Region(view, selections[0])
      space_1 = Util.get_whitespace_from_line_begin(view, sel_1)
      new_text = Util.replace_with_tab(view, sel_1, space_1+"\n"+space_1+"if (bool) {\n"+space_1, "\n"+space_1+"} ")
      view.replace(edit, sel_1, new_text.strip())

      sel_2 = Util.trim_Region(view, selections[1])
      space_2 = Util.get_whitespace_from_line_begin(view, sel_2)
      new_text = Util.replace_with_tab(view, sel_2, " else {\n"+space_2, "\n"+space_2+"}\n"+space_2)
      view.replace(edit, sel_2, new_text.strip())
    else :
      for selection in selections :
        selection = Util.trim_Region(view, selection)
        if view.substr(selection).strip() == "" :
          continue
        space = Util.get_whitespace_from_line_begin(view, selection)

        if case == "if_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"if (bool) {\n"+space, "\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "while_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"while (bool) {\n"+space, "\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "do_while_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"do {\n"+space, "\n"+space+"} while (bool);\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "for_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"for ( ; bool ; ) {\n"+space, "\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "try_catch_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"try {\n"+space, "\n"+space+"} catch (e) {\n"+space+"\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "try_finally_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"try {\n"+space, "\n"+space+"} finally {\n"+space+"\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "try_catch_finally_statement" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"try {\n"+space, "\n"+space+"} catch (e) {\n"+space+"\n"+space+"} finally {\n"+space+"\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "function" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"function () {\n"+space, "\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)

        elif case == "block" :
          new_text = Util.replace_with_tab(view, selection, space+"\n"+space+"{\n"+space, "\n"+space+"}\n"+space)
          view.replace(edit, selection, new_text)
          
  def is_enabled(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    selections = view.sel()
    for selection in selections :
      if view.substr(selection).strip() != "" :
        return True
    return False

  def is_visible(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    selections = view.sel()
    for selection in selections :
      if view.substr(selection).strip() != "" :
        return True
    return False

class delete_surroundedCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    selections = view.sel()
    case = args.get("case")
    for selection in selections :
      scope = view.scope_name(selection.begin()).strip()
      scope_splitted = scope.split(" ")
      if case == "strip_quoted_string" :
        result = Util.firstIndexOfMultiple(scope_splitted, ("string.quoted.double.js", "string.quoted.single.js", "string.template.js"))
        selector = result.get("string")
        item = Util.get_region_scope_first_match(view, scope, selection, selector)
        if item :
          region_scope = item.get("region")
          new_str = item.get("region_string")
          new_str = new_str[1:-1]
          view.replace(edit, region_scope, new_str)

  def is_enabled(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    return True
    
  def is_visible(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    return True

class sort_arrayCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    node = NodeJS()
    view = self.view
    selections = view.sel()
    for selection in selections :
      scope = view.scope_name(selection.begin()).strip()
      result = Util.get_region_scope_first_match(view, scope, selection, "meta.brackets.js")
      if result :
        region = result.get("region")
        array_string = result.get("region_string_stripped")
        node = NodeJS()
        case = args.get("case")
        sort_func = ""
        if case == "compare_func_desc" :
          sort_func = "function(x,y){return y-x;}"
        elif case == "compare_func_asc" :
          sort_func = "function(x,y){return x-y;}"
        elif case == "alpha_asc" :
          sort_func = ""
        elif case == "alpha_desc" :
          sort_func = ""
        sort_result = node.eval("var array = "+array_string+"; console.log(array.sort("+sort_func+")"+( ".reverse()" if case == "alpha_desc" else "" )+")").strip()
        view.replace(edit, region, sort_result)

  def is_enabled(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    selections = view.sel()
    for selection in selections :
      scope = view.scope_name(selection.begin()).strip()
      index = Util.split_string_and_find(scope, "meta.brackets.js")
      if index < 0 :
        return False
    return True

  def is_visible(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    selections = view.sel()
    for selection in selections :
      scope = view.scope_name(selection.begin()).strip()
      index = Util.split_string_and_find(scope, "meta.brackets.js")
      if index < 0 :
        return False
    return True

import re

class create_class_from_object_literalCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    selections = view.sel()
    for selection in selections :
      scope = view.scope_name(selection.begin()).strip()
      depth_level = Util.split_string_and_find(scope, "meta.object-literal.js")
      item_object_literal = Util.get_region_scope_first_match(view, scope, selection, "meta.object-literal.js")

      if item_object_literal :

        scope = item_object_literal.get("scope")
        object_literal_region = item_object_literal.get("region")
        selection = item_object_literal.get("selection")
        object_literal = item_object_literal.get("region_string_stripped")
        node = NodeJS()
        object_literal = re.sub(r'[\n\r\t]', ' ', object_literal)
        object_literal = json.loads(node.eval("JSON.stringify("+object_literal+")", "print"))
        object_literal = [(key, json.dumps(value)) for key, value in object_literal.items()]

        list_ordered = ("keyword.operator.assignment.js", "variable.other.readwrite.js", "storage.type.js")
        items = Util.find_regions_on_same_depth_level(view, scope, selection, list_ordered, depth_level, False)
        if items :
          last_selection = items[-1:][0].get("selection")
          class_name = items[1].get("region_string_stripped")
          regions = [(item.get("region")) for item in items]
          regions.append(object_literal_region)
          regions = Util.cover_regions(regions)
          parameters = list()
          constructor_body = list()
          get_set = list()
          for parameter in object_literal: 
            parameters.append( parameter[0] + ( "="+parameter[1] if json.loads(parameter[1]) != "required" else "") )
            constructor_body.append( "\t\tthis."+parameter[0]+" = "+parameter[0]+";" )
            get_set.append("\tget "+parameter[0]+"() {\n\t\treturn this."+parameter[0]+";\n\t}")
            get_set.append("\tset "+parameter[0]+"("+parameter[0]+") {\n\t\tthis."+parameter[0]+" = "+parameter[0]+";\n\t}")
          parameters = ", ".join(parameters)
          constructor_body = '\n'.join(constructor_body)
          get_set = '\n\n'.join(get_set)
          js_syntax  = "class "+class_name+" {\n"
          js_syntax += "\n\tconstructor ("+parameters+") {\n"
          js_syntax += constructor_body
          js_syntax += "\n\t}\n\n"
          js_syntax += get_set
          js_syntax += "\n\n}"
          js_syntax = Util.add_whitespace_indentation(view, regions, js_syntax)
          view.replace(edit, regions, js_syntax)

  def is_enabled(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    selection = view.sel()[0]
    scope = view.scope_name(selection.begin()).strip()
    index = Util.split_string_and_find(scope, "meta.object-literal.js")
    if index < 0 :
      return False
    return True

  def is_visible(self, **args) :
    view = self.view
    if not Util.selection_in_js_scope(view) :
      return False
    selection = view.sel()[0]
    scope = view.scope_name(selection.begin()).strip()
    index = Util.split_string_and_find(scope, "meta.object-literal.js")
    if index < 0 :
      return False
    return True
      
class split_string_lines_to_variableCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    selections = view.sel()
    for selection in selections :
      scope = view.scope_name(selection.begin()).strip()
      scope_splitted = scope.split(" ")
      case = args.get("case")
      if case == "split" :
        result = Util.firstIndexOfMultiple(scope_splitted, ("string.quoted.double.js", "string.quoted.single.js", "string.template.js"))
        scope_string = scope_splitted[result.get("index")]
        selector = result.get("string")
        item = Util.get_region_scope_first_match(view, scope, selection, selector)
        if item :
          lines = item.get("region_string_stripped")[1:-1].split("\n")
          str_splitted = list()
          str_splitted.append("let str = \"\"")
          for line in lines :
            line = line if scope_string == "string.template.js" else line.strip()[0:-1]
            line = line.strip()
            if line :
              str_splitted.append( "str += "+"%r"%line )
          str_splitted = "\n".join(str_splitted)
          str_splitted = Util.add_whitespace_indentation(view, selection, str_splitted, "\n")
          view.replace(edit, item.get("region"), str_splitted)
          
  def is_visible(self, **args) :
    view = self.view
    if Util.split_string_and_find(view.scope_name(0), "source.js") < 0 :
      return False
    selection = view.sel()[0]
    scope = view.scope_name(selection.begin()).strip()
    scope_splitted = scope.split(" ")
    result = Util.firstIndexOfMultiple(scope_splitted, ("string.quoted.double.js", "string.quoted.single.js", "string.template.js"))
    if result.get("index") < 0 :
      return False
    return True

import sublime, sublime_plugin
import sys, imp, os, webbrowser, re, cgi

class JavaScriptCompletions():

  def get(self, key):
    return sublime.load_settings('JavaScript Enhancements.sublime-settings').get(key)

javascriptCompletions = JavaScriptCompletions()

import sublime, sublime_plugin
import os, tempfile

# list of threads that are used to check if there are 
# multiple async completions tooltip queued (fix for tooltip stuttering)
javascript_completions_thread_list = []

def build_type_from_func_details(comp_details):
  if comp_details :

    paramText = ""
    for param in comp_details["params"]:
      if not paramText:
        paramText += param['name'] + (": " + param['type'] if param['type'] else "")
      else:
        paramText += ", " + param['name'] + (": " + param['type'] if param['type'] else "")

    return ("("+paramText+")" if paramText else "()") + " => " + comp_details["return_type"]

  return ""

def build_completion_snippet(name, params):
  snippet = name + '({})'
  paramText = ''

  count = 1
  for param in params:
    if not paramText:
      paramText += "${" + str(count) + ":" + param['name'] + "}"
    else:
      paramText += ', ' + "${" + str(count) + ":" + param['name'] + "}"
    count = count + 1

  return snippet.format(paramText)

def create_completion(comp_name, comp_type, comp_details) :
  t = tuple()
  t += (comp_name + '\t' + comp_type, )
  t += (build_completion_snippet(
      comp_name,
      comp_details["params"]
    )
    if comp_details else comp_name, )
  return t

class javascript_completionsEventListener(sublime_plugin.EventListener):
  completions = None
  completions_ready = False
  searching = False
  modified = False

  # Used for async completions.
  def run_auto_complete(self):
    sublime.active_window().active_view().run_command("auto_complete", {
      'disable_auto_insert': True,
      'api_completions_only': False,
      'next_completion_if_showing': False,
      'auto_complete_commit_on_tab': True
    })

  def on_query_completions(self, view, prefix, locations):
    # Return the pending completions and clear them

    if not view.match_selector(
        locations[0],
        'source.js - string - comment'
    ):
      return

    view = sublime.active_window().active_view()

    scope = view.scope_name(view.sel()[0].begin()-1).strip()

    # added "keyword.operator.accessor.js" for JavaScript (Babel) support
    if not prefix and not (scope.endswith(" punctuation.accessor.js") or scope.endswith(" keyword.operator.accessor.js")) :
      sublime.active_window().active_view().run_command(
        'hide_auto_complete'
      )
      return []

    if self.completions_ready and self.completions:
      self.completions_ready = False
      return self.completions

    if not self.searching:
      self.searching = True
      self.modified = False
    else: 
      return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    sublime.set_timeout_async(
      lambda: self.on_query_completions_async(
        view, prefix, locations
      )
    )
    
    if not self.completions_ready or not self.completions:
      return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

  def on_query_completions_async(self, view, prefix, locations):

    self.completions = None

    if not view.match_selector(
        locations[0],
        'source.js - string - comment'
    ):
      return

    deps = flow_parse_cli_dependencies(view, add_magic_token=True, cursor_pos=locations[0])

    flow_cli = "flow"
    is_from_bin = True
    chdir = ""
    use_node = True
    bin_path = ""

    settings = get_project_settings()
    if settings and settings["project_settings"]["flow_cli_custom_path"]:
      flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
      bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
      is_from_bin = False
      chdir = settings["project_dir_name"]
      use_node = False

    if self.modified == True:
      self.searching = False
      return

    node = NodeJS(check_local=True)
    
    result = node.execute_check_output(
      flow_cli,
      [
        'autocomplete',
        '--from', 'sublime_text',
        '--root', deps.project_root,
        '--json',
        deps.filename
      ],
      is_from_bin=is_from_bin,
      use_fp_temp=True, 
      fp_temp_contents=deps.contents, 
      is_output_json=True,
      chdir=chdir,
      bin_path=bin_path,
      use_node=use_node
    )

    if result[0]:

      if self.modified == True:
        self.searching = False
        return


          
      result = result[1]
      self.completions = list()
      for match in result['result'] :

        comp_name = match['name']
        comp_type = match['type'] if match['type'] else build_type_from_func_details(match.get('func_details'))

        if comp_type.startswith("((") or comp_type.find("&") >= 0 :
          sub_completions = comp_type.split("&")
          for sub_comp in sub_completions :
            sub_comp = sub_comp.strip()
            sub_type = sub_comp[1:-1] if comp_type.startswith("((") else sub_comp
            
            if not match.get('func_details') :
              text_params = sub_type[ : sub_type.rfind(" => ") if sub_type.rfind(" => ") >= 0 else None ]
              text_params = text_params.strip()
              match["func_details"] = dict()
              match["func_details"]["params"] = list()
              start = 1 if sub_type.find("(") == 0 else sub_type.find("(")+1
              end = text_params.rfind(")")
              params = text_params[start:end].split(",")
              for param in params :
                param_dict = dict()
                param_info = param.split(":")
                param_dict["name"] = param_info[0].strip()
                match['func_details']["params"].append(param_dict)

            completion = create_completion(comp_name, sub_type, match.get('func_details'))
            self.completions.append(completion)
        else :
          completion = create_completion(comp_name, comp_type, match.get('func_details'))
          self.completions.append(completion)

      self.completions += load_default_autocomplete(view, self.completions, prefix, locations[0])
      self.completions = (self.completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
      self.completions_ready = True

      view = sublime.active_window().active_view()
      sel = view.sel()[0]

      if view.substr(view.word(sel)).strip() :

        if self.modified == True:
          self.searching = False
          return
        
        sublime.active_window().active_view().run_command(
          'hide_auto_complete'
        )
        self.run_auto_complete()

    self.searching = False


  def on_text_command(self, view, command_name, args):
    sel = view.sel()[0]
    if not view.match_selector(
        sel.begin(),
        'source.js - string - comment'
    ):
      return

    if command_name == "left_delete" :
      self.modified = True
      self.searching = False
      scope = view.scope_name(view.sel()[0].begin()-1).strip()
      if scope.endswith(" punctuation.accessor.js") or scope.endswith(" keyword.operator.accessor.js"):
        sublime.active_window().active_view().run_command(
          'hide_auto_complete'
        )

    elif command_name == "drag_select" :
      if view.sel()[0].begin() < view.word(view.sel()[0].begin()).end():
        self.modified = True
        self.searching = False

  def on_selection_modified_async(self, view) :

    selections = view.sel()
    if len(selections) == 0:
      return
      
    sel = selections[0]
    if not view.match_selector(
        sel.begin(),
        'source.js - string - comment'
    ):
      return

    scope1 = view.scope_name(sel.begin()-1).strip()
    scope2 = view.scope_name(sel.begin()-2).strip()

    if (scope1.endswith(" punctuation.accessor.js") or scope1.endswith(" keyword.operator.accessor.js")) and not (scope2.endswith(" punctuation.accessor.js") or scope2.endswith(" keyword.operator.accessor.js")) and view.substr(sel.begin()-2).strip() :
      
      locations = list()
      locations.append(sel.begin())

      if not self.searching:
        self.searching = True
        self.modified = False
      else: 
        return 

      sublime.set_timeout_async(
        lambda: self.on_query_completions_async(
          view, "", locations
        )
      )


import sublime, sublime_plugin
import os



class go_to_defCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    view = self.view
    if args and "point" in args :
      point = args["point"]
    else :
      point = view.sel()[0].begin()
    point = view.word(point).begin()
    self.go_to_def(view, point)

  def go_to_def(self, view, point):
    view = sublime.active_window().active_view()
    view.sel().clear()
    #sublime.active_window().run_command("goto_definition")

    #if view.sel()[0].begin() == point :
    # try flow get-def
    sublime.set_timeout_async(lambda : self.find_def(view, point))

  def find_def(self, view, point) :
    view.sel().add(point)

    deps = flow_parse_cli_dependencies(view)
    
    flow_cli = "flow"
    is_from_bin = True
    chdir = ""
    use_node = True
    bin_path = ""

    settings = get_project_settings()
    if settings and settings["project_settings"]["flow_cli_custom_path"]:
      flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
      bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
      is_from_bin = False
      chdir = settings["project_dir_name"]
      use_node = False
      
    node = NodeJS(check_local=True)

    result = node.execute_check_output(
      flow_cli,
      [
        'get-def',
        '--from', 'sublime_text',
        '--root', deps.project_root,
        '--json',
        ':temp_file',
        str(deps.row + 1), str(deps.col + 1)
      ],
      is_from_bin=is_from_bin,
      use_fp_temp=True, 
      fp_temp_contents=deps.contents, 
      is_output_json=True,
      use_only_filename_view_flow=True,
      chdir=chdir,
      bin_path=bin_path,
      use_node=use_node
    )

    if result[0] :
      row = result[1]["line"]-1
      col = result[1]["start"]-1
      if result[1]["path"] != "-" and os.path.isfile(result[1]["path"]) :
        view = sublime.active_window().open_file(result[1]["path"])     
      Util.go_to_centered(view, row, col)

  def is_enabled(self):
    view = self.view
    if not Util.selection_in_js_scope(view):
      return False
    return True

  def is_visible(self):
    view = self.view
    if not Util.selection_in_js_scope(view, -1, "- string - comment"):
      return False
    return True

js_css = ""
with open(os.path.join(JC_SETTINGS_FOLDER, "style.css")) as css_file:
  js_css = "<style>"+css_file.read()+"</style>"

default_completions = Util.open_json(os.path.join(PACKAGE_PATH, 'default_autocomplete.json')).get('completions')

def load_default_autocomplete(view, comps_to_campare, prefix, location, isHover = False):

  if not prefix :
    return []
  
  scope = view.scope_name(location-(len(prefix)+1)).strip()

  if scope.endswith(" punctuation.accessor.js") or scope.endswith(" keyword.operator.accessor.js") :
    return []

  prefix = prefix.lower()
  completions = default_completions
  completions_to_add = []
  for completion in completions: 
    c = completion[0].lower()
    if not isHover:
      if c.startswith(prefix):
        completions_to_add.append((completion[0], completion[1]))
    else :
      if len(completion) == 3 and c.startswith(prefix) :
        completions_to_add.append(completion[2])
  final_completions = []
  for completion in completions_to_add:
    flag = False
    for c_to_campare in comps_to_campare:
      if not isHover and completion[0].split("\t")[0] == c_to_campare[0].split("\t")[0] :
        flag = True
        break
      elif isHover and completion["name"] == c_to_campare["name"] :
        flag = True
        break
    if not flag :
      final_completions.append(completion)

  return final_completions

import sublime, sublime_plugin

def description_details_html(description):
  description_name = "<span class=\"name\">" + cgi.escape(description['name']) + "</span>"
  description_return_type = ""

  text_pre_params = ""

  parameters_html = ""
  if description['func_details'] :

    if not description['type'].startswith("(") :
      text_pre_params = description['type'][ : description['type'].rfind(" => ") if description['type'].rfind(" => ") >= 0 else None ]
      text_pre_params = "<span class=\"text-pre-params\">" + cgi.escape(text_pre_params[:text_pre_params.find("(")]) + "</span>"

    for param in description['func_details']["params"]:
      is_optional = True if param['name'].find("?") >= 0 else False
      param['name'] = cgi.escape(param['name'].replace("?", ""))
      param['type'] = cgi.escape(param['type']) if param.get('type') else None
      if not parameters_html:
        parameters_html += "<span class=\"parameter-name\">" + param['name'] + "</span>" + ( "<span class=\"parameter-is-optional\">?</span>" if is_optional else "" ) + ( ": <span class=\"parameter-type\">" + param['type'] + "</span>" if param['type'] else "" )
      else:
        parameters_html += ', ' + "<span class=\"parameter-name\">" + param['name'] + "</span>" + ( "<span class=\"parameter-is-optional\">?</span>" if is_optional else "" ) + ( ": <span class=\"parameter-type\">" + param['type'] + "</span>" if param['type'] else "" )
    parameters_html = "("+parameters_html+")"

    description_return_type = cgi.escape(description['func_details']["return_type"]) if description['func_details']["return_type"] else ""
  elif description['type'] :
    description_return_type = cgi.escape(description['type'])
  if description_return_type :
    description_return_type = " => <span class=\"return-type\">"+description_return_type+"</span>"

  html = """ 
  <div class=\"container-description\">
    <div>"""+description_name+text_pre_params+parameters_html+description_return_type+"""</div>
    <div class=\"container-go-to-def\"><a href="go_to_def" class="go-to-def">Go to definition</a></div>
  </div>
  """
  return html

class on_hover_descriptionEventListener(sublime_plugin.EventListener):

  def on_hover(self, view, point, hover_zone) :
    if not view.match_selector(
        point,
        'source.js - string - constant - comment'
    ):
      return

    if hover_zone != sublime.HOVER_TEXT :
      return

    for region in view.get_regions("flow_error"):
      if region.contains(point):
        return

    region = view.word(point)
    word = view.substr(region)
    if not word.strip() :
      return

    view.hide_popup()

    sublime.set_timeout_async(lambda: on_hover_description_async(view, point, hover_zone, point))

# used also by show_hint_parametersCommand
def on_hover_description_async(view, point, hover_zone, popup_position, show_hint=False) :
  if not view.match_selector(
      point,
      'source.js - comment'
  ):
    return

  if hover_zone != sublime.HOVER_TEXT :
    return

  if not show_hint:
    for region in view.get_regions("flow_error"):
      if region.contains(point):
        return

  region = view.word(point)
  word = view.substr(region)
  if not word.strip() :
    return

  cursor_pos = region.end()

  deps = flow_parse_cli_dependencies(view, cursor_pos=cursor_pos, add_magic_token=True, not_add_last_part_tokenized_line=True)

  flow_cli = "flow"
  is_from_bin = True
  chdir = ""
  use_node = True
  bin_path = ""

  settings = get_project_settings()
  if settings and settings["project_settings"]["flow_cli_custom_path"]:
    flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
    bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
    is_from_bin = False
    chdir = settings["project_dir_name"]
    use_node = False

  node = NodeJS(check_local=True)

  result = node.execute_check_output(
    flow_cli,
    [
      'autocomplete',
      '--from', 'sublime_text',
      '--root', deps.project_root,
      '--json',
      deps.filename
    ],
    is_from_bin=is_from_bin,
    use_fp_temp=True, 
    fp_temp_contents=deps.contents, 
    is_output_json=True,
    chdir=chdir,
    bin_path=bin_path,
    use_node=use_node
  )

  html = ""
  results_found = 0

  if result[0]:
    descriptions = result[1]["result"] + load_default_autocomplete(view, result[1]["result"], word, region.begin(), True)

    for description in descriptions :
      if description['name'] == word :

        if description['type'].startswith("((") or description['type'].find("&") >= 0 :
          sub_completions = description['type'].split("&")
          for sub_comp in sub_completions :

            results_found += 1

            sub_comp = sub_comp.strip()
            sub_type = sub_comp[1:-1] if description['type'].startswith("((") else sub_comp
                       
            text_params = sub_type[ : sub_type.rfind(" => ") if sub_type.rfind(" => ") >= 0 else None ]
            text_params = text_params.strip()
            description["func_details"] = dict()
            description["func_details"]["params"] = list()
            description["func_details"]["return_type"] = ""
            if sub_type.rfind(" => ") >= 0 :
              description["func_details"]["return_type"] = sub_type[sub_type.rfind(" => ")+4:].strip()
            start = 1 if sub_type.find("(") == 0 else sub_type.find("(")+1
            end = text_params.rfind(")")
            params = text_params[start:end].split(",")
            for param in params :
              param_dict = dict()
              param_info = param.split(":")
              param_dict["name"] = param_info[0].strip()
              if len(param_info) > 1 :
                param_dict["type"] = param_info[1].strip()
              description['func_details']["params"].append(param_dict)

            html += description_details_html(description)
        else :

          html += description_details_html(description)

  if not html :
    deps = flow_parse_cli_dependencies(view)

    row, col = view.rowcol(point)

    flow_cli = "flow"
    is_from_bin = True
    chdir = ""
    use_node = True
    bin_path = ""

    settings = get_project_settings()
    if settings and settings["project_settings"]["flow_cli_custom_path"]:
      flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
      bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
      is_from_bin = False
      chdir = settings["project_dir_name"]
      use_node = False
      
    node = NodeJS(check_local=True)
    result = node.execute_check_output(
      flow_cli,
      [
        'type-at-pos',
        '--from', 'sublime_text',
        '--root', deps.project_root,
        '--path', deps.filename,
        '--json',
        str(row - deps.row_offset + 1), str(col + 1)
      ],
      is_from_bin=is_from_bin,
      use_fp_temp=True, 
      fp_temp_contents=deps.contents, 
      is_output_json=True,
      chdir=chdir,
      bin_path=bin_path,
      use_node=use_node
    )

    if result[0] and result[1].get("type") and result[1]["type"] != "(unknown)":

      results_found = 1

      description = dict()
      description["name"] = ""
      description['func_details'] = dict()
      description['func_details']["params"] = list()
      description['func_details']["return_type"] = ""
      is_function = False
      matches = re.match("^([a-zA-Z_]\w+)", result[1]["type"])
      if matches :
        description["name"] = matches.group()
      if result[1]["type"].find(" => ") >= 0 :
        description['func_details']["return_type"] = cgi.escape(result[1]["type"][result[1]["type"].find(" => ")+4:])
      else :
        description['func_details']["return_type"] = cgi.escape(result[1]["type"])
      if result[1]["type"].find("(") == 0:
        is_function = True
        start = 1
        end = result[1]["type"].find(")")
        params = result[1]["type"][start:end].split(",")
        description['func_details']["params"] = list()
        for param in params :
          param_dict = dict()
          param_info = param.split(":")
          param_dict["name"] = cgi.escape(param_info[0].strip())
          if len(param_info) == 2 :
            param_dict["type"] = cgi.escape(param_info[1].strip())
          else :
            param_dict["type"] = None
          description['func_details']["params"].append(param_dict)

      description_name = "<span class=\"name\">" + cgi.escape(description['name']) + "</span>"
      description_return_type = ""

      parameters_html = ""
      if description['func_details'] :

        for param in description['func_details']["params"]:
          is_optional = True if param['name'].find("?") >= 0 else False
          param['name'] = param['name'].replace("?", "")
          if not parameters_html:
            parameters_html += "<span class=\"parameter-name\">" + param['name'] + "</span>" + ( "<span class=\"parameter-is-optional\">?</span>" if is_optional else "" ) + ( ": <span class=\"parameter-type\">" + param['type'] + "</span>" if param['type'] else "" )
          else:
            parameters_html += ', ' + "<span class=\"parameter-name\">" + param['name'] + "</span>" + ( "<span class=\"parameter-is-optional\">?</span>" if is_optional else "" ) + ( ": <span class=\"parameter-type\">" + param['type'] + "</span>" if param['type'] else "" )
        parameters_html = "("+parameters_html+")" if is_function else ""

        description_return_type = description['func_details']["return_type"]
      elif description['type'] :
        description_return_type = description['type']
      if description_return_type :
        description_return_type = (" => " if description['name'] or is_function else "") + "<span class=\"return-type\">"+description_return_type+"</span>"

      html += """ 
      <div class=\"container-description\">
        <div>"""+description_name+parameters_html+description_return_type+"""</div>
        <div class=\"container-go-to-def\"><a href="go_to_def" class="go-to-def">Go to definition</a></div>
      </div>
      """

  func_action = lambda x: view.run_command("go_to_def", args={"point": point}) if x == "go_to_def" else ""

  if html:
      view.show_popup("""
      <html><head></head><body class=\""""+("single-result-found" if results_found == 1 else "more-results-found")+"""\">
      """+js_css+"""
        <div class=\"container-hint-popup\">
          """ + html + """    
        </div>
      </body></html>""", sublime.COOPERATE_WITH_AUTO_COMPLETE | sublime.HIDE_ON_MOUSE_MOVE_AWAY, popup_position, 1150, 80 if results_found == 1 else 160, func_action )
  

import sublime, sublime_plugin

class show_hint_parametersCommand(sublime_plugin.TextCommand):
  
  # flow doesn't work with meta.function-call.constructor.js
  meta_fun_calls = [
    "meta.function-call.method.js", 
    "meta.function-call.js",
    # JavaScript (Babel) Syntax support
    "meta.function-call.with-arguments.js",
    "meta.function-call.static.with-arguments.js",
    "meta.function-call.method.with-arguments.js",
    "meta.function-call.without-arguments.js",
    "meta.function-call.static.without-arguments.js",
    "meta.function-call.method.without-arguments.js",
    "meta.function-call.tagged-template.js",
    "source.js"
  ]

  meta_groups = [
    "meta.group.js",
    # JavaScript (Babel) Syntax support, this order is important!
    "meta.group.braces.round.function.arguments.js",
    "meta.group.braces.round.js"
  ]

  def run(self, edit, **args):
    view = self.view

    point = view.sel()[0].begin()
    
    meta_group = 0
    mate_group_scope = ""

    for mt in self.meta_groups:
      meta_group = view.scope_name(point).strip().split(" ").count(mt)
      if meta_group > 0:
        mate_group_scope = mt
        break

    if meta_group == 0:
      return

    while point >= 0:
      scope = view.scope_name(point).strip()
      scope_splitted = scope.split(" ")
      if len(scope_splitted) < 2:
        return 

      if scope_splitted[-2] in self.meta_fun_calls and scope_splitted.count(mate_group_scope) == meta_group - 1:
        sublime.set_timeout_async(lambda: on_hover_description_async(view, point, sublime.HOVER_TEXT, view.sel()[0].begin(), show_hint=True))
        return

      point = view.word(point).begin() - 1 if view.substr(point) != "(" else point - 1

  def is_enabled(self) :
    view = self.view
    sel = view.sel()[0]
    if not view.match_selector(
        sel.begin(),
        'source.js - comment'
    ):
      return False

    point = view.sel()[0].begin()
    
    meta_group = 0
    mate_group_scope = ""

    for mt in self.meta_groups:
      meta_group = view.scope_name(point).strip().split(" ").count(mt)
      if meta_group > 0:
        mate_group_scope = mt
        break

    if meta_group == 0:
      return False

    while point >= 0:
      scope = view.scope_name(point).strip()
      scope_splitted = scope.split(" ")
      if len(scope_splitted) < 2:
        return False

      if scope_splitted[-2] in self.meta_fun_calls and scope_splitted.count(mate_group_scope) == meta_group - 1:
        #print(view.substr(view.word(point)))
        return True

      point = view.word(point).begin() - 1 if view.substr(point) != "(" else point - 1

    return False

  def is_visible(self) :
    view = self.view
    sel = view.sel()[0]
    if not view.match_selector(
        sel.begin(),
        'source.js - comment'
    ):
      return False
    
    point = view.sel()[0].begin()
    
    meta_group = 0
    mate_group_scope = ""

    for mt in self.meta_groups:
      meta_group = view.scope_name(point).strip().split(" ").count(mt)
      if meta_group > 0:
        mate_group_scope = mt
        break

    if meta_group == 0:
      return False

    while point >= 0:
      scope = view.scope_name(point).strip()
      scope_splitted = scope.split(" ")
      if len(scope_splitted) < 2:
        return False

      if scope_splitted[-2] in self.meta_fun_calls and scope_splitted.count(mate_group_scope) == meta_group - 1:
        return True

      point = view.word(point).begin() - 1 if view.substr(point) != "(" else point - 1

    return False
    

import sublime, sublime_plugin

def hide_flow_errors(view) :
  view.erase_regions('flow_error')
  view.erase_status('flow_error')

class handle_flow_errorsCommand(sublime_plugin.TextCommand):

  def run(self, edit, **args):
    view = self.view

    if args :
      if args["type"] == "show" :
        sublime.set_timeout_async(lambda: show_flow_errorsViewEventListener(view).on_activated_async())
      elif args["type"] == "hide" :
        hide_flow_errors(view)

  def is_enabled(self):
    view = self.view
    return Util.selection_in_js_scope(view)

  def is_visible(self):
    view = self.view
    return Util.selection_in_js_scope(view)


import sublime, sublime_plugin
import cgi, time

class show_flow_errorsViewEventListener(wait_modified_asyncViewEventListener, sublime_plugin.ViewEventListener):

  description_by_row = {}
  errors = []
  errorRegions = []
  callback_setted_use_flow_checker_on_current_view = False
  prefix_thread_name = "show_flow_errors_view_event_listener"
  wait_time = .15
  modified = False

  def on_activated_async(self):
    self.on_modified_async()

  def on_modified(self):
    self.modified = True

  def on_modified_async(self):
    super(show_flow_errorsViewEventListener, self).on_modified_async()

  def on_selection_modified_async(self):
    view = self.view

    if view.find_by_selector('source.js.embedded.html') and (self.errors or view.get_regions("flow_error")):
      pass

    elif not Util.selection_in_js_scope(view) or not self.errors or not view.get_regions("flow_error"):
      hide_flow_errors(view)
      return

    settings = get_project_settings()
    if settings :
      if not settings["project_settings"]["flow_checker_enabled"] or not is_project_view(view) :
        hide_flow_errors(view)
        return
      elif settings["project_settings"]["flow_checker_enabled"] :
        comments = view.find_by_selector('source.js comment')
        flow_comment_found = False
        for comment in comments:
          if "@flow" in view.substr(comment) :
            flow_comment_found = True
            break
        if not flow_comment_found :
          hide_flow_errors(view)
          return
    elif not view.settings().get("use_flow_checker_on_current_view") :
      hide_flow_errors(view)
      return 

    row, col = view.rowcol(view.sel()[0].begin())

    if self.errors:
      error_count = len(self.errors)
      error_count_text = 'Flow: {} error{}'.format(
        error_count, '' if error_count is 1 else 's'
      )
      error_for_row = self.description_by_row.get(row)
      if error_for_row:
        view.set_status(
          'flow_error', error_count_text + ': ' + error_for_row["description"]
        )
      else:
        view.set_status('flow_error', error_count_text)

  def on_modified_async_with_thread(self, recheck=True):

    self.modified = False

    view = self.view

    if view.find_by_selector('source.js.embedded.html'):
      pass
    elif not Util.selection_in_js_scope(view):
      hide_flow_errors(view)
      return

    settings = get_project_settings()
    if settings :
      if not settings["project_settings"]["flow_checker_enabled"] or not is_project_view(view) :
        hide_flow_errors(view)
        return
      elif settings["project_settings"]["flow_checker_enabled"] :
        comments = view.find_by_selector('source.js comment')
        flow_comment_found = False
        for comment in comments:
          if "@flow" in view.substr(comment) :
            flow_comment_found = True
            break
        if not flow_comment_found :
          hide_flow_errors(view)
          return
    elif not view.settings().get("use_flow_checker_on_current_view") :
      hide_flow_errors(view)
      return 

    self.wait()  

    deps_list = list()
    if view.find_by_selector("source.js.embedded.html") :
      deps_list = flow_parse_cli_dependencies(view, check_all_source_js_embedded=True)
    else :
      deps_list = [flow_parse_cli_dependencies(view)]

    flag = False

    for deps in deps_list:

      flow_cli = "flow"
      is_from_bin = True
      chdir = ""
      use_node = True
      bin_path = ""

      settings = get_project_settings()
      if settings and settings["project_settings"]["flow_cli_custom_path"]:
        flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
        bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
        is_from_bin = False
        chdir = settings["project_dir_name"]
        use_node = False
        
      node = NodeJS(check_local=True)
      
      result = node.execute_check_output(
        flow_cli,
        [
          'check-contents',
          '--from', 'sublime_text',
          '--root', deps.project_root,
          '--json',
          deps.filename
        ],
        is_from_bin=is_from_bin,
        use_fp_temp=True, 
        fp_temp_contents=deps.contents, 
        is_output_json=True,
        clean_output_flow=True,
        chdir=chdir,
        bin_path=bin_path,
        use_node=use_node
      )

      if not flag:
        self.errors = []
        self.description_by_row = {}
        self.description_by_row_column = {}
        self.errorRegions = []
        flag = True

      if result[0]:

        if result[1]['passed']:
          continue

        for error in result[1]['errors']:
          description = ''
          operation = error.get('operation')
          row = -1
          for i in range(len(error['message'])):
            message = error['message'][i]
            if i == 0 :
              row = int(message['line']) + deps.row_offset - 1
              endrow = int(message['endline']) + deps.row_offset - 1
              col = int(message['start']) - 1
              endcol = int(message['end'])

              self.errorRegions.append(Util.rowcol_to_region(view, row, endrow, col, endcol))

              if operation:
                description += operation["descr"]

            if not description :
              description += "'"+message['descr']+"'"
            else :
              description += " " + message['descr']

          if row >= 0 :
            row_description = self.description_by_row.get(row)
            if not row_description:
              self.description_by_row[row] = {
                "col": col,
                "description": description
              }
            if row_description and description not in row_description:
              self.description_by_row[row]["description"] += '; ' + description

            self.description_by_row_column[str(row)+":"+str(endrow)+":"+str(col)+":"+str(endcol)] = description
              
        self.errors += result[1]['errors']

    if not self.modified :
      view.erase_regions('flow_error')
      if self.errorRegions:
        view.add_regions( 'flow_error', self.errorRegions, 'keyword', 'dot', sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE )
      else:
        view.erase_status("flow_error")
    elif (recheck) :
      sublime.set_timeout_async(lambda: self.on_modified_async_with_thread(recheck=False))


  def on_hover(self, point, hover_zone) :
    view = self.view

    if view.find_by_selector('source.js.embedded.html') and (self.errors or view.get_regions("flow_error")):
      pass

    elif not Util.selection_in_js_scope(view) or not self.errors or not view.get_regions("flow_error"):
      hide_flow_errors(view)
      return

    if hover_zone != sublime.HOVER_TEXT :
      return

    sel = sublime.Region(point, point)

    is_hover_error = False
    region_hover_error = None
    for region in view.get_regions("flow_error"):
      if region.contains(sel):
        region_hover_error = region
        is_hover_error = True
        break

    if not is_hover_error:
      return
    
    settings = get_project_settings()
    if settings :
      if not settings["project_settings"]["flow_checker_enabled"] or not is_project_view(view) :
        hide_flow_errors(view)
        return
      elif settings["project_settings"]["flow_checker_enabled"] :
        comments = view.find_by_selector('source.js comment')
        flow_comment_found = False
        for comment in comments:
          if "@flow" in view.substr(comment) :
            flow_comment_found = True
            break
        if not flow_comment_found :
          hide_flow_errors(view)
          return
    elif not view.settings().get("use_flow_checker_on_current_view") :
      hide_flow_errors(view)
      return 

    row_region, col_region = view.rowcol(region_hover_error.begin())
    end_row_region, endcol_region = view.rowcol(region_hover_error.end())

    error = self.description_by_row_column[str(row_region)+":"+str(end_row_region)+":"+str(col_region)+":"+str(endcol_region)]
    
    if error:
      text = cgi.escape(error).split(" ")
      html = ""
      i = 0
      while i < len(text) - 1:
        html += text[i] + " " + text[i+1] + " "
        i += 2
        if i % 10 == 0 :
          html += " <br> "
      if len(text) % 2 != 0 :
        html += text[len(text) - 1]

      row_region, col_region = view.rowcol(region_hover_error.begin())
      end_row_region, endcol_region = view.rowcol(region_hover_error.end())
      
      view.show_popup('<html style="padding: 0px; margin: 0px; background-color: rgba(255,255,255,1);"><body style="font-size: 0.8em; font-weight: bold; padding: 5px; background-color: #F44336; margin: 0px;">'+html+'<br><a style="margin-top: 10px; display: block; color: #000;" href="copy_to_clipboard">Copy</a></body></html>', sublime.HIDE_ON_MOUSE_MOVE_AWAY, point, 1150, 80, lambda action: sublime.set_clipboard(error) or view.hide_popup() )




import sublime, sublime_plugin

class navigate_flow_errorsCommand(navigate_regionsCommand, sublime_plugin.TextCommand):

  region_key = "flow_error"

import sublime, sublime_plugin
import traceback, os, json, io, sys, imp,shlex, tempfile

class evaluate_javascriptCommand(manage_cliCommand):

  isNode = True
  alsoNonProject = True

  def prepare_command(self, **kwargs):

    is_line = kwargs.get("is_line") if "is_line" in kwargs else False

    view = self.window.active_view()
    sel = view.sel()[0]
    region_selected = None
    str_selected = view.substr(sel).strip()

    if is_line:
      lines = view.lines(sel)
      region_selected = lines[0]
      str_selected = view.substr(region_selected)
    else: 
      if not str_selected and region_selected : 
        region = get_start_end_code_highlights_eval()
        region_selected = sublime.Region(region[0], region[1])
        lines = view.lines(region_selected)
        str_selected = ""
        for line in lines:
          str_selected += view.substr(view.full_line(line))
      elif str_selected:
        lines = view.lines(sel)
        region_selected = sublime.Region if not region_selected else region_selected
        region_selected = sublime.Region(lines[0].begin(), lines[-1:][0].end())
      elif not str_selected :
        return
    
    if not region_selected :
      return

    fp = tempfile.NamedTemporaryFile(delete=False)
    fp.write(str.encode("console.log('\\n'); console.time('Execution Time');\n"+str_selected+"\nconsole.log('\\n'); console.timeEnd('Execution Time');"))
    fp.close()

    if sublime.platform() == "windows":
      self.command = ["-p", "<", json.dumps(fp.name), "&", "del", "/f", "/q", json.dumps(fp.name)]
    else :
      self.command = ["-p", "<", shlex.quote(fp.name), ";", "rm", "-rf", shlex.quote(fp.name)]

    self._run()
    
  def _run(self):
    super(evaluate_javascriptCommand, self)._run()

  def is_enabled(self, **args) :
    view = self.window.active_view()
    if not Util.selection_in_js_scope(view) :
      return False
    return True

  def is_visible(self, **args) :
    view = self.window.active_view()
    if not Util.selection_in_js_scope(view) :
      return False
    return True

import sublime, sublime_plugin
import json, time

bookmarks = dict()

def set_bookmarks(set_dot = False, erase_regions = True):
  global bookmarks
  view = sublime.active_window().active_view()
  
  if is_project_view(view) and is_javascript_project() :
    project_settings = get_project_settings()
    bookmarks = Util.open_json(os.path.join(project_settings["settings_dir_name"], 'bookmarks.json')) or dict()
  else :
    sublime.error_message("Can't recognize JavaScript Project.")
    return

  if erase_regions:
    view.erase_regions("region-dot-bookmarks")
    if set_dot :
      lines = []
      lines = [view.line(view.text_point(bookmark_line, 0)) for bookmark_line in search_bookmarks_by_view(view, is_from_set = True)]
      view.add_regions("region-dot-bookmarks", lines,  "code", "bookmark", sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

def update_bookmarks(set_dot = False, erase_regions = True):
  global bookmarks
  path = ""
  view = sublime.active_window().active_view()

  if is_project_view(view) and is_javascript_project() :
    project_settings = get_project_settings()
    path = os.path.join(project_settings["settings_dir_name"], 'bookmarks.json')
  else :
    sublime.error_message("Can't recognize JavaScript Project.")
    return

  with open(path, 'w+') as bookmarks_json:
    bookmarks_json.write(json.dumps(bookmarks))

  if erase_regions:
    view.erase_regions("region-dot-bookmarks")
    if set_dot :
      lines = []
      lines = [view.line(view.text_point(bookmark_line, 0)) for bookmark_line in search_bookmarks_by_view(view)]
      view.add_regions("region-dot-bookmarks", lines,  "code", "bookmark", sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)

def get_bookmark_by_line(view, line, is_project = False):
  if not view.file_name() or line < 0:
    return False

  global bookmarks

  if is_project :
    set_bookmarks(True, True, False)
  else :
    set_bookmarks(False, True, False)

  for bookmark in bookmarks:
    if bookmark['file_name'] == view.file_name() and bookmark["line"] == line :
      return bookmark

  return None

def add_bookmark(view, line) :
  if not view.file_name() or line < 0:
    return False

  global bookmarks

  set_bookmarks(True)

  if not view.file_name() in bookmarks:
    bookmarks[view.file_name()] = [line]
  elif not line in bookmarks[view.file_name()]:
    bookmarks[view.file_name()].append(line)
    
  update_bookmarks(True)

def overwrite_bookmarks(view, lines) :
  if not view.file_name():
    return False

  global bookmarks

  bookmarks[view.file_name()] = lines
  update_bookmarks(True)

def remove_bookmarks(view) :

  if not view.file_name():
    return False

  set_bookmarks(True)

  global bookmarks

  if view.file_name() in bookmarks :
    del bookmarks[view.file_name()]
    update_bookmarks(True)

def remove_bookmark_by_line(view, line) :

  if not view.file_name() or line < 0:
    return False

  set_bookmarks(True)

  global bookmarks

  if view.file_name() in bookmarks and line in bookmarks[view.file_name()] :
    bookmarks[view.file_name()].remove(line)
    update_bookmarks(True)

def search_bookmarks_by_view(view, is_from_set = False):
  if not view.file_name():
    return []

  global bookmarks

  if not is_from_set :
    set_bookmarks(True)

  return bookmarks[view.file_name()] if view.file_name() in bookmarks else []

def open_bookmarks_and_show(file_name, line) :

  view = sublime.active_window().open_file(file_name)

  sublime.set_timeout_async(lambda: Util.go_to_centered(view, line, 0))

class toggle_project_bookmarksCommand(sublime_plugin.TextCommand) :

  def run(self, edit):

    view = self.view

    if view.get_regions("region-dot-bookmarks"):
      view.erase_regions("region-dot-bookmarks")
    else:
      set_bookmarks(True)

  def is_enabled(self):
    return True if is_project_view(self.view) and is_javascript_project() else False

  def is_visible(self):
    return True if is_project_view(self.view) and is_javascript_project() else False    

class add_project_bookmark_hereCommand(sublime_plugin.TextCommand) :

  def run(self, edit):

    view = self.view

    for sel in view.sel():
      row, col = view.rowcol(sel.begin())
      add_bookmark(view, row)

  def is_enabled(self):
    return True if is_project_view(self.view) and is_javascript_project() else False

  def is_visible(self):
    return True if is_project_view(self.view) and is_javascript_project() else False

class show_project_bookmarksCommand(sublime_plugin.TextCommand):

  def run(self, edit, **args) :
    global bookmarks

    window = sublime.active_window()
    view = self.view

    show_type = args.get("type")

    set_bookmarks(True, True)

    if not bookmarks:
      return 

    items = []

    if show_type == "global_project" :

      for file_name in bookmarks.keys():
        for item in bookmarks[file_name]:
          items += [ ["line: " + str(item+1), file_name] ]

    elif show_type == "view_project" : 

      bookmarks_view = search_bookmarks_by_view(view)

      for item in bookmarks_view:
        items += [ ["line: " + str(item+1), view.file_name()] ]
    
    if items : 
      window.show_quick_panel(items, lambda index: open_bookmarks_and_show(items[index][1], int(items[index][0].replace("line: ", ""))-1 ) if index != -1 else None )

  def is_enabled(self):
    return is_javascript_project()

  def is_visible(self):
    return is_javascript_project()

class delete_project_bookmarksCommand(sublime_plugin.TextCommand):

  def run(self, edit, **args) :
    global bookmarks

    window = sublime.active_window()
    view = self.view

    show_type = args.get("type")

    if show_type == "global_project" :

      bookmarks = dict()
      update_bookmarks(True)

    elif show_type == "view" or show_type == "view_project" : 

      remove_bookmarks(view)

    elif show_type == "single_view_project" : 

      bookmarks_view = search_bookmarks_by_view(view)

      items = []

      for item in bookmarks_view:
        items += [ ["line: " + str(item+1), view.file_name()] ]

      window.show_quick_panel(items, lambda index: remove_bookmark_by_line( view, int(items[index][0].replace("line: ", ""))-1 ) if index != -1 else None )

  def is_enabled(self):
    return is_javascript_project()

  def is_visible(self):
    return is_javascript_project()

class navigate_project_bookmarksCommand(navigate_regionsCommand, sublime_plugin.TextCommand):

  region_key = "region-dot-bookmarks" 

class update_bookmarks_lineEventListener(sublime_plugin.EventListener):

  def on_post_save_async(self, view) :

    if is_project_view(view) and is_javascript_project(): 
      regions = view.get_regions("region-dot-bookmarks")

      lines = []
      for region in regions:
        row, col = view.rowcol(region.begin())
        lines += [row]

      if lines:
        overwrite_bookmarks( view, lines )


class add_jsdoc_conf(sublime_plugin.WindowCommand) :
  def run(self, **args):
    settings = get_project_settings()
    if settings :
      if not settings['project_settings']['jsdoc']['conf_file']:
        settings['project_settings']['jsdoc']['conf_file'] = "conf.json"
        save_project_setting('project_settings.json', settings['project_settings'])
      jsdoc_conf_file = os.path.join(settings['project_dir_name'], settings['project_settings']['jsdoc']['conf_file'])
      shutil.copyfile( os.path.join(HELPER_FOLDER, "jsdoc", "conf-default.json"), jsdoc_conf_file )
  
  def is_enabled(self):
    return True if is_javascript_project() else False

class generate_jsdocCommand(manage_cliCommand):

  isNode = True
  isBinPath = True

  def prepare_command(self):

    jsdoc_conf_file = self.settings['project_settings']['jsdoc']['conf_file']
    if os.path.isfile(jsdoc_conf_file) :
      self.command = ["jsdoc", "-c", jsdoc_conf_file]

    else :
      sublime.error_message("JSDOC ERROR: Can't load "+jsdoc_conf_file+" file!\nConfiguration file REQUIRED!")
      return  

    self._run()

  def _run(self):
    super(generate_jsdocCommand, self)._run()

  def is_enabled(self):
    return True if is_javascript_project() else False

import sublime, sublime_plugin
import re

class expand_abbreviationCommand(sublime_plugin.TextCommand):

  def run(self, edit, *args) :

    view = self.view

    for sel in view.sel():

      row, col = view.rowcol(sel.begin())

      string = view.substr(sel).strip()

      index = string.rfind("*")

      n_times = int(string[index+1:])

      string = string[:index]

      final_string =  ""
      string_pieces = re.split(r"\$+", string)
      delimeters = re.findall(r"(\$+)", string)

      for x in range(1, n_times+1):
        for y in range(len(string_pieces)):
          if y < len(string_pieces) - 1:
            final_string += string_pieces[y] + str(x).zfill(len(delimeters[y]))
          else :
            final_string += string_pieces[y] + "\n" + ( " " * col)

      view.replace(edit, sel, final_string)

  def is_enabled(self) :

    view = self.view

    sel = view.sel()[0]
    string = view.substr(sel).strip()
    index = string.rfind("*")
    if index >= 0 :
      try :
        int(string[index+1:])
        return True
      except ValueError as e:
        pass

    return False

  def is_visible(self) :

    view = self.view

    sel = view.sel()[0]
    string = view.substr(sel).strip()
    index = string.rfind("*")
    if index >= 0 :
      try :
        int(string[index+1:])
        return True
      except ValueError as e:
        pass

    return False

items_found_can_i_use = None
can_i_use_file = None
can_i_use_popup_is_showing = False
can_i_use_list_from_main_menu = False
path_to_can_i_use_data = os.path.join(HELPER_FOLDER, "can_i_use", "can_i_use_data.json")
path_to_test_can_i_use_data = os.path.join(HELPER_FOLDER, "can_i_use", "can_i_use_data2.json")
url_can_i_use_json_data = "https://raw.githubusercontent.com/Fyrd/caniuse/master/data.json"

can_i_use_css = ""
with open(os.path.join(HELPER_FOLDER, "can_i_use", "style.css")) as css_file:
  can_i_use_css = "<style>"+css_file.read()+"</style>"

def donwload_can_i_use_json_data() :
  global can_i_use_file

  if os.path.isfile(path_to_can_i_use_data) :
    with open(path_to_can_i_use_data) as json_file:    
      try :
        can_i_use_file = json.load(json_file)
      except Exception as e :
        print("Error: "+traceback.format_exc())
        sublime.active_window().status_message("Can't use \"Can I use\" json data from: https://raw.githubusercontent.com/Fyrd/caniuse/master/data.json")

  if Util.download_and_save(url_can_i_use_json_data, path_to_test_can_i_use_data) :
    if os.path.isfile(path_to_can_i_use_data) :
      if not Util.checksum_sha1_equalcompare(path_to_can_i_use_data, path_to_test_can_i_use_data) :
        json_file = open(path_to_test_can_i_use_data) 
        try :
          can_i_use_file = json.load(json_file)
          if os.path.isfile(path_to_can_i_use_data) :
            os.remove(path_to_can_i_use_data)
          json_file.close()
          os.rename(path_to_test_can_i_use_data, path_to_can_i_use_data)
        except Exception as e :
          print("Error: "+traceback.format_exc())
          sublime.active_window().status_message("Can't use new \"Can I use\" json data from: https://raw.githubusercontent.com/Fyrd/caniuse/master/data.json")
        if not json_file.closed:
          json_file.close()
      if os.path.isfile(path_to_test_can_i_use_data) :
        if not json_file.closed:
          json_file.close()
        try :
          os.remove(path_to_test_can_i_use_data)
        except Exception as e :
          pass
    else :
      os.rename(path_to_test_can_i_use_data, path_to_can_i_use_data)
      with open(path_to_can_i_use_data) as json_file :    
        try :
          can_i_use_file = json.load(json_file)
        except Exception as e :
          print("Error: "+traceback.format_exc())
          sublime.active_window().status_message("Can't use \"Can I use\" json data from: https://raw.githubusercontent.com/Fyrd/caniuse/master/data.json")

Util.create_and_start_thread(donwload_can_i_use_json_data, "DownloadCanIuseJsonData")

def find_in_can_i_use(word) :
  global can_i_use_file
  can_i_use_data = can_i_use_file.get("data")
  word = word.lower()
  return [value for key, value in can_i_use_data.items() if value["title"].lower().find(word) >= 0]

def back_to_can_i_use_list(action):
  global can_i_use_popup_is_showing
  if action.find("http") >= 0:
    webbrowser.open(action)
    return
  view = sublime.active_window().active_view()
  can_i_use_popup_is_showing = False
  view.hide_popup()
  if len(action.split(",")) > 1 and action.split(",")[1] == "main-menu" :
    view.run_command("can_i_use", args={"from": "main-menu"})
  else :  
    view.run_command("can_i_use")

def show_pop_can_i_use(index):
  global can_i_use_file
  global items_found_can_i_use
  global can_i_use_popup_is_showing
  if index < 0:
    return
  item = items_found_can_i_use[index]

  browser_accepted = ["ie", "edge", "firefox", "chrome", "safari", "opera", "ios_saf", "op_mini", "android", "and_chr"]
  browser_name = [
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;IE",
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;EDGE",
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Firefox", 
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Chrome", 
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Safari", 
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Opera", 
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;iOS Safari", 
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Opera Mini", 
    "&nbsp;&nbsp;&nbsp;Android Browser", 
    "Chrome for Android"
  ]

  html_browser = ""

  html_browser += "<div>"
  html_browser += "<h1 class=\"title\">"+cgi.escape(item["title"])+" <a href=\""+item["spec"].replace(" ", "%20")+"\"><span class=\"status "+item["status"]+"\"> - "+item["status"].upper()+"</span></a></h1>"
  html_browser += "<p class=\"description\">"+cgi.escape(item["description"])+"</p>"
  html_browser += "<p class=\"\"><span class=\"support\">Global Support: <span class=\"support-y\">"+str(item["usage_perc_y"])+"%</span>"+( " + <span class=\"support-a\">"+str(item["usage_perc_a"])+"%</span> = " if float(item["usage_perc_a"]) > 0 else "" )+( "<span class=\"support-total\">"+str( "{:10.2f}".format(float(item["usage_perc_y"]) + float(item["usage_perc_a"])) )+"%</span>" if float(item["usage_perc_a"]) > 0 else "" )+"</span> "+( " ".join(["<span class=\"category\">"+category+"</span>" for category in item["categories"]]) )+"</p>"
  html_browser += "</div>"

  html_browser += "<div class=\"container-browser-list\">"
  i = 0
  for browser in browser_accepted :

    browser_versions = can_i_use_file["agents"]
    stat = item["stats"].get(browser)
    stat_items_ordered = list()
    for k in stat.keys() :
      if k != "TP" : 
        stat_items_ordered.append(k)

    if len(stat_items_ordered) >= 1 and stat_items_ordered[0] != "all" :
      stat_items_ordered.sort(key=LooseVersion)
      stat_items_ordered = stat_items_ordered[::-1]

    html_p = "<p class=\"version-stat-item\"><span class=\"browser-name\">"+browser_name[i]+"</span> : "
    j = 0
    while j < len(stat_items_ordered) :
      if j == 7:
        break
      class_name = stat.get(stat_items_ordered[j])
      html_annotation_numbers = ""
      requires_prefix = ""
      can_be_enabled = ""

      if re.search(r"\bx\b", class_name) :
        requires_prefix = "x"
      if re.search(r"\bd\b", class_name) :
        can_be_enabled = "d"

      if class_name.find("#") >= 0 :
        numbers = class_name[class_name.find("#"):].strip().split(" ")
        for number in numbers :
          number = int(number.replace("#", ""))
          html_annotation_numbers += "<span class=\"annotation-number\">"+str(number)+"</span>"

      html_p += "<span class=\"version-stat "+stat.get(stat_items_ordered[j])+" \">"+( html_annotation_numbers if html_annotation_numbers else "" )+stat_items_ordered[j]+( "<span class=\"can-be-enabled\">&nbsp;</span>" if can_be_enabled else "" )+( "<span class=\"requires-prefix\">&nbsp;</span>" if requires_prefix else "" )+"</span> "

      j = j + 1

    html_p += "</p>"
    html_browser += html_p
    i = i + 1

  html_browser += "</div>"

  if item["notes_by_num"] :
    html_browser += "<div>"
    html_browser += "<h3>Notes</h3>"
    notes_by_num = item["notes_by_num"]

    notes_by_num_ordered = list()
    for k in notes_by_num.keys() :
      notes_by_num_ordered.append(k)
    notes_by_num_ordered.sort()

    i = 0
    while i < len(notes_by_num_ordered) :
      note = notes_by_num.get(notes_by_num_ordered[i])
      html_p = "<p class=\"note\"><span class=\"annotation-number\">"+str(notes_by_num_ordered[i])+"</span>"+cgi.escape(note)+"</p>"
      html_browser += html_p
      i = i + 1
    html_browser += "</div>"

  if item["links"] :
    html_browser += "<div>"
    html_browser += "<h3>Links</h3>"
    links = item["links"]

    for link in links :
      html_p = "<p class=\"link\"><a href=\""+link.get("url")+"\">"+cgi.escape(link.get("title"))+"</a></p>"
      html_browser += html_p
    html_browser += "</div>"

  view = sublime.active_window().active_view()
  
  can_i_use_popup_is_showing = True
  view.show_popup("""
    <html>
      <head></head>
      <body>
      """+can_i_use_css+"""
      <div class=\"container-back-button\">
        <a class=\"back-button\" href=\"back"""+( ",main-menu" if can_i_use_list_from_main_menu else "")+"""\">&lt; Back</a>
        <a class=\"view-on-site\" href=\"http://caniuse.com/#search="""+item["title"].replace(" ", "%20")+"""\"># View on \"Can I use\" site #</a>
      </div>
      <div class=\"content\">
        """+html_browser+"""
        <div class=\"legend\">
          <h3>Legend</h3>
          <div class=\"container-legend-items\">
            <span class=\"legend-item y\">&nbsp;</span> = Supported 
            <span class=\"legend-item n\">&nbsp;</span> = Not Supported 
            <span class=\"legend-item p a\">&nbsp;</span> = Partial support 
            <span class=\"legend-item u\">&nbsp;</span> = Support unknown 
            <span class=\"legend-item requires-prefix\">&nbsp;</span> = Requires Prefix 
            <span class=\"legend-item can-be-enabled\">&nbsp;</span> = Can Be Enabled 
          </div>
        </div>
      </div>
      </body>
    </html>""", sublime.COOPERATE_WITH_AUTO_COMPLETE, -1, 1250, 650, back_to_can_i_use_list)

class can_i_useCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):

    global items_found_can_i_use
    global can_i_use_file
    global can_i_use_list_from_main_menu

    if not can_i_use_file:
      sublime.active_window().status_message("\"Can I use\" feature is not ready.")
      return

    can_i_use_data = can_i_use_file.get("data")
    if not can_i_use_data :
      return

    view = self.view
    selection = view.sel()[0]
    if args.get("from") != "main-menu" :
      can_i_use_list_from_main_menu = False
      word = view.substr(view.word(selection)).strip()
      items_found_can_i_use = find_in_can_i_use(word)
      sublime.active_window().show_quick_panel([item["title"] for item in items_found_can_i_use], show_pop_can_i_use)
    else :
      can_i_use_list_from_main_menu = True
      items_found_can_i_use = find_in_can_i_use("")
      sublime.active_window().show_quick_panel([item["title"] for item in items_found_can_i_use], show_pop_can_i_use)
  
  def is_enabled(self, **args):
    view = self.view
    if args.get("from") == "main-menu" or javascriptCompletions.get("enable_can_i_use_menu_option") :
      return True 
    return False

  def is_visible(self, **args):
    view = self.view
    if args.get("from") == "main-menu" :
      return True
    if javascriptCompletions.get("enable_can_i_use_menu_option") :
      if Util.split_string_and_find_on_multiple(view.scope_name(0), ["source.js", "text.html.basic", "source.css"]) < 0 :
        return False
      return True
    return False
    
class can_i_use_hide_popupEventListener(sublime_plugin.EventListener):
  def on_selection_modified_async(self, view) :
    global can_i_use_popup_is_showing
    if can_i_use_popup_is_showing :
      view.hide_popup()
      can_i_use_popup_is_showing = False

import sublime, sublime_plugin

class unused_variablesViewEventListener(wait_modified_asyncViewEventListener, sublime_plugin.ViewEventListener):

  unusedVariableRegions = []
  prefix_thread_name = "unused_variables"
  wait_time = .15
  modified = False

  def on_activated_async(self):
    self.on_modified_async()

  def on_modified(self):
    self.modified = True

  def on_modified_async(self):
    super(unused_variablesViewEventListener, self).on_modified_async()

  def on_selection_modified_async(self):

    view = self.view

    if not javascriptCompletions.get("enable_unused_variables_feature"):
      view.erase_status("unused_variables")
      view.erase_regions("unused_variables")
      return 
    elif view.find_by_selector('source.js.embedded.html'):
      pass
    elif not Util.selection_in_js_scope(view):
      view.erase_status("unused_variables")
      view.erase_regions("unused_variables")
      return

    statusInRegion = ""
    for region in self.unusedVariableRegions:
      if region.contains(view.sel()[0]):
        statusInRegion = "'" + view.substr(region) + "'"

    if self.unusedVariableRegions:
      if statusInRegion:
        view.set_status("unused_variables", str(len(self.unusedVariableRegions)) + " unused variables: " + statusInRegion )
      else:
        view.set_status("unused_variables", str(len(self.unusedVariableRegions)) + " unused variables" )

  def on_modified_async_with_thread(self, recheck=True):

    self.modified = False

    view = self.view

    if not javascriptCompletions.get("enable_unused_variables_feature"):
      view.erase_status("unused_variables")
      view.erase_regions("unused_variables")
      return 
    elif view.find_by_selector('source.js.embedded.html'):
      pass
    elif not Util.selection_in_js_scope(view):
      view.erase_status("unused_variables")
      view.erase_regions("unused_variables")
      return

    self.wait()

    deps_list = list()
    if view.find_by_selector("source.js.embedded.html") :
      deps_list = flow_parse_cli_dependencies(view, check_all_source_js_embedded=True)
    else :
      deps_list = [flow_parse_cli_dependencies(view)]

    flag = False

    for deps in deps_list:
      flow_cli = "flow"
      is_from_bin = True
      chdir = ""
      use_node = True
      bin_path = ""

      settings = get_project_settings()
      if settings and settings["project_settings"]["flow_cli_custom_path"]:
        flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
        bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
        is_from_bin = False
        chdir = settings["project_dir_name"]
        use_node = False

      node = NodeJS(check_local=True)
      
      result = node.execute_check_output(
        flow_cli,
        [
          'ast',
          '--from', 'sublime_text'
        ],
        is_from_bin=is_from_bin,
        use_fp_temp=True, 
        fp_temp_contents=deps.contents, 
        is_output_json=True,
        chdir=chdir,
        bin_path=bin_path,
        use_node=use_node
      )

      repetitions = dict()

      if result[0]:
        
        if "body" in result[1]:
          body = result[1]["body"]
          items = Util.nested_lookup("type", ["VariableDeclarator", "FunctionDeclaration", "ClassDeclaration", "ImportDefaultSpecifier", "ImportNamespaceSpecifier", "ImportSpecifier", "ArrayPattern", "ObjectPattern"], body)
          for item in items:

            if "id" in item and isinstance(item["id"],dict) and "name" in item["id"] and item["id"]["type"] == "Identifier":
              item = item["id"]

            elif "local" in item and isinstance(item["local"],dict) and "name" in item["local"] and item["local"]["type"] == "Identifier":
              item = item["local"]

            elif "properties" in item:
              for prop in item["properties"]:
                if prop["type"] == "Property" and "key" in prop and isinstance(prop["key"],dict) and "name" in prop["key"] and prop["key"]["type"] == "Identifier":
                  items += [prop["key"]]
              continue

            elif "elements" in item:
              for element in item["elements"]:
                if isinstance(element,dict) and "name" in element and element["type"] == "Identifier":
                  items += [element]
              continue

            #else :
            #  item = Util.nested_lookup("type", ["Identifier"], item)[0]

            variableName = ""
            try:
              variableName = item["name"]
            except (KeyError) as e:
              continue
            startRegion = view.text_point(int(item["loc"]["start"]["line"]) + deps.row_offset - 1, int(item["loc"]["start"]["column"]))
            endRegion = view.text_point(int(item["loc"]["end"]["line"]) + deps.row_offset - 1, int(item["loc"]["end"]["column"]))
            variableRegion = sublime.Region(startRegion, endRegion) 

            scope = view.scope_name(variableRegion.begin()-1).strip()
            scope_splitted = scope.split(" ")

            if scope.endswith(" punctuation.accessor.js") or scope.endswith(" keyword.operator.accessor.js"):
              continue

            if view.substr(view.line(variableRegion)).strip().startswith("export") and not scope.startswith("source.js meta.export.js meta.block.js") and not scope.startswith("source.js meta.group.braces.curly.js") and len(scope_splitted) <= 4:
              continue  

            repetitions[variableName] = [variableRegion]

          items = Util.nested_lookup("type", ["VariableDeclarator", "MemberExpression", "CallExpression", "BinaryExpression", "ExpressionStatement", "Property", "ArrayExpression", "ObjectPattern", "AssignmentExpression", "IfStatement", "ForStatement", "WhileStatement", "ForInStatement", "ForOfStatement", "LogicalExpression", "UpdateExpression", "ArrowFunctionExpression", "ConditionalExpression", "JSXIdentifier", "ExportDefaultDeclaration", "JSXExpressionContainer", "NewExpression", "ReturnStatement", "SpreadProperty", "TemplateLiteral"], body)
          for item in items:

            if "exportKind" in item and "declaration" in item and isinstance(item["declaration"],dict) and "name" in item["declaration"] and item["declaration"]["type"] == "Identifier":
              item = item["declaration"]

            elif "object" in item :
              if "property" in item and isinstance(item["property"],dict) and "name" in item["property"] and item["property"]["type"] == "Identifier":
                items += [item["property"]]
              if "object" in item and isinstance(item["object"],dict) and "name" in item["object"] and item["object"]["type"] == "Identifier":
                item = item["object"]
              else:
                continue

            elif "callee" in item :    
              if "arguments" in item:
                for argument in item["arguments"]:
                  if isinstance(argument,dict) and "name" in argument and argument["type"] == "Identifier":
                    items += [argument]
                  elif "expressions" in argument and argument["expressions"]:
                    for expression in argument["expressions"]:
                      if isinstance(expression,dict) and "name" in expression and expression["type"] == "Identifier":
                        items += [expression]

              item = item["callee"]

            elif "expressions" in item and item["expressions"]:
              for expression in item["expressions"]:
                if isinstance(expression,dict) and "name" in expression and expression["type"] == "Identifier":
                  items += [expression]
              continue

            elif "left" in item or "right" in item:

              if "left" in item and isinstance(item["left"],dict) and "name" in item["left"] and item["left"]["type"] == "Identifier":
                items += [item["left"]]
              if "right" in item and isinstance(item["right"],dict) and "name" in item["right"] and item["right"]["type"] == "Identifier":
                items += [item["right"]]

            elif "test" in item:
              if "consequent" in item and isinstance(item["consequent"],dict) and "name" in item["consequent"] and item["consequent"]["type"] == "Identifier":
                items += [item["consequent"]]
              if "alternate" in item and isinstance(item["alternate"],dict) and "name" in item["alternate"] and item["alternate"]["type"] == "Identifier":
                items += [item["alternate"]]
              if isinstance(item["test"],dict) and "name" in item["test"] and item["test"]["type"] == "Identifier":
                item = item["test"]
              else:
                continue

            elif "expression" in item and isinstance(item["expression"],dict) and "name" in item["expression"] and item["expression"]["type"] == "Identifier":
              item = item["expression"]

            elif "argument" in item and isinstance(item["argument"],dict) and "name" in item["argument"] and item["argument"]["type"] == "Identifier":
              item = item["argument"]

            elif "elements" in item :
              for element in item["elements"]:
                if isinstance(element,dict) and "name" in element and element["type"] == "Identifier":
                  items += [element]
              continue

            elif "value" in item and isinstance(item["value"],dict) and "name" in item["value"] and item["value"]["type"] == "Identifier":
              item = item["value"]

            elif "init" in item and isinstance(item["init"],dict) and "name" in item["init"] and item["init"]["type"] == "Identifier":
              item = item["init"]

            elif "body" in item and isinstance(item["body"],dict) and "name" in item["body"] and item["body"]["type"] == "Identifier":
              item = item["body"]

            variableName = ""
            try:
              variableName = item["name"]
            except (KeyError) as e:
              continue

            startRegion = view.text_point(int(item["loc"]["start"]["line"]) + deps.row_offset - 1, int(item["loc"]["start"]["column"]))
            endRegion = view.text_point(int(item["loc"]["end"]["line"]) + deps.row_offset - 1, int(item["loc"]["end"]["column"]))
            variableRegion = sublime.Region(startRegion, endRegion) 

            scope = view.scope_name(variableRegion.begin()-1).strip()

            if scope.endswith(" punctuation.accessor.js") or scope.endswith(" keyword.operator.accessor.js"):
              continue

            if variableName in repetitions and not variableRegion in repetitions[variableName]:
              repetitions[variableName] += [variableRegion]

          if not flag:
            self.unusedVariableRegions = [] 
            flag = True
          
          errorRegions = view.get_regions("flow_error")
          for variableName in repetitions.keys():
            count = len(repetitions[variableName])
            if count == 1:
              intersects = False
              for errorRegion in errorRegions:
                if errorRegion.intersects(repetitions[variableName][0]):
                  intersects = True
                  break
              if not intersects:
                self.unusedVariableRegions += [repetitions[variableName][0]]

    if not self.modified :
      view.erase_regions("unused_variables")
      if self.unusedVariableRegions:
        view.add_regions("unused_variables", self.unusedVariableRegions, "string", "dot", sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE)
      else:
        view.erase_status("unused_variables")
    elif (recheck) :
        sublime.set_timeout_async(lambda: self.on_modified_async_with_thread(recheck=False))

class navigate_unused_variablesCommand(navigate_regionsCommand, sublime_plugin.TextCommand):

  region_key = "unused_variables"

import sublime, sublime_plugin

class sort_javascript_importsCommand(sublime_plugin.TextCommand):

  def run(self, edit, **args):
    view = self.view

    if "imports" in args and "regionPoints" in args:
      imports = args.get('imports')
      regionPoints = args.get('regionPoints')
      first_line = view.substr(view.full_line(0)).strip()
      first_line_empty = True if not first_line or not first_line.startswith("import") else False
      if regionPoints:
        for i in range(1, len(regionPoints)+1):
          regionPoint = regionPoints[-i]
          region = sublime.Region(regionPoint[0], regionPoint[1])
          full_line = view.substr(view.full_line(region)).replace(view.substr(region), '').strip()
          if not full_line:
            region = sublime.Region(regionPoint[0]-1, regionPoint[1])
          view.erase(edit, region)

        if view.match_selector(0, 'comment'):
          comment = view.extract_scope(0)
          view.replace(edit, sublime.Region(comment.end(), comment.end()), "\n" + "\n".join(sorted(imports)))
        elif first_line_empty:
          view.replace(edit, sublime.Region(0,0), "\n".join(sorted(imports)) + "\n\n")
        else:
          view.replace(edit, sublime.Region(0,0), "\n".join(sorted(imports)))

    else:
      sublime.set_timeout_async(self.get_imports)

  def get_imports(self):

    view = self.view

    deps = flow_parse_cli_dependencies(view)

    flow_cli = "flow"
    is_from_bin = True
    chdir = ""
    use_node = True
    bin_path = ""

    settings = get_project_settings()
    if settings and settings["project_settings"]["flow_cli_custom_path"]:
      flow_cli = os.path.basename(settings["project_settings"]["flow_cli_custom_path"])
      bin_path = os.path.dirname(settings["project_settings"]["flow_cli_custom_path"])
      is_from_bin = False
      chdir = settings["project_dir_name"]
      use_node = False

    node = NodeJS(check_local=True)
    
    result = node.execute_check_output(
      flow_cli,
      [
        'ast',
        '--from', 'sublime_text'
      ],
      is_from_bin=is_from_bin,
      use_fp_temp=True, 
      fp_temp_contents=deps.contents, 
      is_output_json=True,
      chdir=chdir,
      bin_path=bin_path,
      use_node=use_node
    )

    if result[0]:
      if "body" in result[1]:
        body = result[1]["body"]
        items = Util.nested_lookup("type", ["ImportDeclaration"], body)
        imports = []
        regionPoints = []
        for item in items:
          row = int(item['loc']['start']['line']) - 1
          endrow = int(item['loc']['end']['line']) - 1
          col = int(item['loc']['start']['column']) - 1
          endcol = int(item['loc']['end']['column'])

          startRegion = view.text_point(row, col)
          endRegion = view.text_point(endrow, endcol)
          regionPoints += [[startRegion, endRegion]]

          importRegion = sublime.Region(startRegion, endRegion) 

          imports += [view.substr(importRegion)]

        view.run_command('sort_javascript_imports', args={"imports": imports, "regionPoints": regionPoints})
  
  def is_enabled(self):
    view = self.view
    if not Util.selection_in_js_scope(view) and view.find_by_selector('source.js.embedded.html'):
      return False

    if view.find_by_selector('meta.import.js'):
      return True

    # try JavaScript (Babel) syntax
    import_regions = view.find_by_selector('keyword.operator.module.js')
    for import_region in import_regions:
      if (view.substr(import_region).startswith("import")) :
        return True

    return False

  def is_visible(self):
    view = self.view
    if not Util.selection_in_js_scope(view) and view.find_by_selector('source.js.embedded.html'):
      return False

    if view.find_by_selector('meta.import.js'):
      return True

    # try JavaScript (Babel) syntax
    import_regions = view.find_by_selector('keyword.operator.module.js')
    for import_region in import_regions:
      if (view.substr(import_region).startswith("import")) :
        return True

    return False


# import sublime, sublime_plugin
# import re


#   { "caption": "-" },
#   {
#     "caption": "Refactor (Working on it ...)",
#     "id": "refactor",
#     "children": [
#       {
#         "caption": "Extract",
#         "children": [
#           {
#             "caption": "Method",
#             "command": "refactor",
#             "args": {"case": "extract_method"}
#           }
#         ]
#       }
#     ]
#   }

# class refactorCommand(sublime_plugin.TextCommand):
#   def run(self, edit, **args):
#     view = self.view
#     case = args.get("case")
#     if not "answer" in args :
#       caption = ""
#       initial_text = ""

#       if case == "extract_method" :
#         caption = "Method:"
#         initial_text = "func ()"

#       view.window().show_input_panel(caption, initial_text, lambda answer: view.run_command('refactor', args={"case": case, "answer": answer}), None, None)
#     else :
#       answer = args.get("answer").strip()
#       scope = view.scope_name(view.sel()[0].begin())
#       space = Util.get_whitespace_from_line_begin(view, view.sel()[0])
#       if case == "extract_method" :
#         new_text = Util.replace_with_tab(view, view.sel()[0], "\t\n\t"+answer+" {\n\t", "\n\t}\n")
#         view.replace(edit, view.sel()[0], "this."+(re.sub('\s+\(', '(', answer)) )
#         region_class = Util.get_region_scope_first_match(view, scope, view.sel()[0], 'meta.class.js')["region"]
#         view.insert(edit, region_class.end()-1, new_text)

#   def is_enabled(self, **args) :
#     view = self.view
#     if not Util.selection_in_js_scope(view) :
#       return False
#     selections = view.sel()
#     for selection in selections :
#       if view.substr(selection).strip() != "" :
#         return True
#     return False

#   def is_visible(self, **args) :
#     view = self.view
#     if not Util.selection_in_js_scope(view) :
#       return False
#     selections = view.sel()
#     for selection in selections :
#       if view.substr(selection).strip() != "" :
#         return True
#     return False

def start():

  global mainPlugin

  print("JavaScript Enhancements plugin version: "+PLUGIN_VERSION)

  if platform.architecture()[0] != "64bit":
    print(platform.architecture())
    sublime.error_message("Your architecture is not supported by this plugin. This plugin supports only 64bit architectures.")
    return

  if sublime.platform() != 'windows':
    try:
      sys.modules["TerminalView"]
    except Exception as err:
      response = sublime.yes_no_cancel_dialog("TerminalView plugin is missing. TerminalView is required to be able to use \"JavaScript Enhancements\" plugin.\n\nDo you want open the github repo of it?", "Yes, open it", "No")
      if response == sublime.DIALOG_YES:
        sublime.active_window().run_command("open_url", args={"url": "https://github.com/Wramberg/TerminalView"})
      return

  try:
    sys.modules["JavaScript Completions"]
    sublime.error_message("Please uninstall/disable my other plugin \"JavaScript Completions\". It could conflict with this one!")
    return
  except Exception as err:
    pass

  node = NodeJS(check_local=True)
  try:
    print("node.js version: " + str(node.getCurrentNodeJSVersion()))
  except Exception as err: 
    print(err)
    response = sublime.yes_no_cancel_dialog("Error during installation: \"node.js\" seems not installed on your system. Node.js and npm are required to be able to use JavaScript Enhancements plugin.\n\nIf you are using \"nvm\" or you have a different path for node.js and npm, please then change the path on:\n\nPreferences > Package Settings > JavaScript Enhancements > Settings\n\nand restart Sublime Text. If you don't know the path of it, use \"which node\" (for Linux-based OS) or \"where node.exe\" (for Windows OS) to get it.\n\nIf this doesn't work then try also to add the path of their binaries in the PATH key-value on the same JavaScript Enhancements settings file. This variable will be used to add them in the $PATH environment variable, so put the symbol \":\" (instead \";\" for Windows) in front of your path.\n\nDo you want open the website of node.js?", "Yes, open it", "Or use nvm")
    if response == sublime.DIALOG_YES:
      sublime.active_window().run_command("open_url", args={"url": "https://nodejs.org"})
    elif response == sublime.DIALOG_NO:
      sublime.active_window().run_command("open_url", args={"url": "https://github.com/creationix/nvm"})
    return

  npm = NPM(check_local=True)
  try:
    print("npm version: " + str(npm.getCurrentNPMVersion()))
  except Exception as err: 
    print(err)
    response = sublime.yes_no_cancel_dialog("Error during installation: \"npm\" seems not installed on your system. Node.js and npm are required to be able to use JavaScript Enhancements plugin.\n\nIf you are using \"nvm\" or you have a different path for node.js and npm, please change their custom path on:\n\nPreferences > Package Settings > JavaScript Enhancements > Settings\n\nand restart Sublime Text. If you don't know the path of it, use \"which npm\" (for Linux-based OS) or \"where npm\" (for Windows OS) to get it.\n\nIf this doesn't work then try also to add the path of their binaries in the PATH key-value on the same JavaScript Enhancements settings file. This variable will be used to add them in the $PATH environment variable, so put the symbol \":\" (instead \";\" for Windows) in front of your path.\n\nDo you want open the website of node.js?", "Yes, open it", "Or use nvm")
    if response == sublime.DIALOG_YES:
      sublime.active_window().run_command("open_url", args={"url": "https://nodejs.org"})
    elif response == sublime.DIALOG_NO:
      sublime.active_window().run_command("open_url", args={"url": "https://github.com/creationix/nvm"})
    return

  mainPlugin.init()

##
## start - Fix Mac Path plugin code with some fixes
##

fixPathSettings = None
fixPathOriginalEnv = {}

def getSysPath():
  command = ""
  if platform.system() == "Darwin":
    command = "TERM=ansi CLICOLOR=\"\" SUBLIME=1 /usr/bin/login -fqpl $USER $SHELL -l -c 'TERM=ansi CLICOLOR=\"\" SUBLIME=1 printf \"%s\" \"$PATH\"'"
  elif platform.system() == "Linux":
    command = "TERM=ansi CLICOLOR=\"\" SUBLIME=1 $SHELL --login -c 'TERM=ansi CLICOLOR=\"\" printf \"%s\" $PATH'"
  else:
    return ""

  # Execute command with original environ. Otherwise, our changes to the PATH propogate down to
  # the shell we spawn, which re-adds the system path & returns it, leading to duplicate values.
  sysPath = Popen(command, stdout=PIPE, shell=True, env=fixPathOriginalEnv).stdout.read()

  sysPathString = sysPath.decode("utf-8")
  # Remove ANSI control characters (see: http://www.commandlinefu.com/commands/view/3584/remove-color-codes-special-characters-with-sed )
  sysPathString = re.sub(r'\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]', '', sysPathString)
  sysPathString = sysPathString.strip().rstrip(':')

  # Decode the byte array into a string, remove trailing whitespace, remove trailing ':'
  return sysPathString

def fixPath():
  currSysPath = getSysPath()
  # Basic sanity check to make sure our new path is not empty
  if len(currSysPath) < 1:
    return False

  environ['PATH'] = currSysPath

  for pathItem in fixPathSettings.get("additional_path_items", []):
    environ['PATH'] = pathItem + ':' + environ['PATH']

  return True


def plugin_unloaded():
  if platform.system() == "Darwin" or platform.system() == "Linux":
    # When we unload, reset PATH to original value. Otherwise, reloads of this plugin will cause
    # the PATH to be duplicated.
    environ['PATH'] = fixPathOriginalEnv['PATH']

    global fixPathSettings
    fixPathSettings.clear_on_change('fixpath-reload')

  node = NodeJS(check_local=True)
  sublime.set_timeout_async(lambda: node.execute("flow", ["stop"], is_from_bin=True, chdir=os.path.join(PACKAGE_PATH, "flow")))

##
## end - Fix Mac Path plugin code
##

def plugin_loaded():
  
  if int(sublime.version()) >= 3124 :

    if platform.system() == "Darwin" or platform.system() == "Linux":
      global fixPathSettings
      fixPathSettings = sublime.load_settings("Preferences.sublime-settings")
      fixPathSettings.clear_on_change('fixpath-reload')
      fixPathSettings.add_on_change('fixpath-reload', fixPath)

      # Save the original environ (particularly the original PATH) to restore later
      global fixPathOriginalEnv
      for key in environ:
        fixPathOriginalEnv[key] = environ[key]

      fixPath()

    sublime.set_timeout_async(start, 1000)

  else:
    response = sublime.yes_no_cancel_dialog("JavaScript Enhancements plugin requires Sublime Text 3 (build 3124 or newer). Your build is: " + sublime.version() + ". Do you want open the download page?", "Yes, open it", "No")
    if response == sublime.DIALOG_YES:
      sublime.active_window().run_command("open_url", args={"url": "https://www.sublimetext.com/3"})

