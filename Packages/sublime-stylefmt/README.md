# sublime-stylefmt
Sublime Text plugin for [Stylefmt](https://github.com/morishitter/stylefmt)

## Install

### Package Control

Install `Stylefmt` with [Package Control](https://packagecontrol.io/packages/Stylefmt) and restart Sublime.

**You need to have [Node.js](http://nodejs.org) installed.**  
Make sure it's in your $PATH by running `node -v` in your command-line.

> Note: On OS X it's expected that Node resides in the /usr/local/bin/ folder, which it does when installed with the default installer. If this is not the case, symlink your Node binary to this location:  
`ln -s /full/path/to/your/node /usr/local/bin/node`

### Add Repository

1) Open the Command Palette (Windows and Linux: <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>p</kbd>, OSX: <kbd>cmd</kbd>+<kbd>shift</kbd>+<kbd>p</kbd>)

2) Select *Package Control > Add Repository*

3) Paste in https://github.com/dmnsgn/sublime-stylefmt

## Usage 

### Command Palette

Use the Command Pallete (Windows and Linux: <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>p</kbd>, OSX: <kbd>cmd</kbd>+<kbd>shift</kbd>+<kbd>p</kbd>) and run:

> Run Stylefmt

## Options

*(Preferences > Package Settings > Stylefmt > Settings - User)*

The *format on save* functionality can be extended to be applied on specific syntaxes or extensions.

```json
{
  "formatOnSave": false,
  "syntaxes": ["SCSS"],
  "extensions": [".scss"]
}
```

### Project settings

You can override the default and user settings for individual projects. Just add an `"Stylefmt"` object to the `"settings"` object in the project's `.sublime-project` file containing your [project specific settings](http://www.sublimetext.com/docs/3/projects.html).

Example:

```json
{
	"settings": {
		"Stylefmt": {
			"formatOnSave": false,
			"syntaxes": ["SCSS"],
			"extensions": [".scss"]
		}
	}
}
```

### Keyboard shortcut

You can also set up a keyboard shortcut to run the command by opening up *Preferences > Key Bindings - User* and adding your shortcut with the `stylefmt` command.

Example:

```json
[
	{ "keys": ["alt+super+f"], "command": "stylefmt" }
]
```

## License

Based on [FixMyJS plugin](https://github.com/addyosmani/sublime-fixmyjs) by Addy Osmani.

ISC © [Damien Seguin](http://dmnsgn.me)
