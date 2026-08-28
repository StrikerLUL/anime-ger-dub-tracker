const fs = require('fs');
const js = fs.readFileSync('extracted.js', 'utf8');

// The file ends with "    </script>" so there's an issue with the regex maybe?
// Actually wait, let me just check syntax with node
