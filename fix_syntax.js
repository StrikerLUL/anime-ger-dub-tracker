const fs = require('fs');
const acorn = require('acorn');

const code = fs.readFileSync('Anime Synchro Tracker v11.0.1.html', 'utf-8');
const scriptMatch = code.match(/<script>([\s\S]*?)<\/script>/);

if (scriptMatch) {
  const jsCode = scriptMatch[1];
  try {
    acorn.parse(jsCode, { ecmaVersion: 2020 });
    console.log("No syntax error found.");
  } catch (e) {
    console.log("Syntax error at line", e.loc.line, "col", e.loc.column);
    console.log(e.message);
    const lines = jsCode.split('\n');
    console.log("Code around error:");
    for (let i = Math.max(0, e.loc.line - 5); i < Math.min(lines.length, e.loc.line + 5); i++) {
      console.log(`${i+1}: ${lines[i]}`);
    }
  }
}
