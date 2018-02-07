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

