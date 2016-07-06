'use strict';

var stylefmt = require('stylefmt');
var data = '';

// Get options if needed
if (process.argv.length > 2) {
  var opts = JSON.parse(process.argv[2]);
  process.chdir(opts.file_path);
}

process.stdin.on('data', function(css) {
  data += css;
});

process.stdin.on('end', function() {
  stylefmt.process(data).then(function(result) {
    try {
      process.stdout.write(result.css);
    } catch (err) {
      throw err;
    }
  });
});
