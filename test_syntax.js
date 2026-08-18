const fs = require('fs');
const content = fs.readFileSync('./Anime Synchro Tracker v11.0.1.html', 'utf8');
const scriptMatch = content.match(/<script>(.*?)<\/script>/s);
if (scriptMatch) {
  try {
    const acorn = require('acorn');
    acorn.parse(scriptMatch[1], {ecmaVersion: 2020, locations: true});
    console.log("Syntax is OK");
  } catch(e) {
    console.error("Syntax Error at line", e.loc.line, "col", e.loc.column, ": ", e.message);
  }
}
