import { divideNumbers, parseNumericInput } from "./calculator";

// Basic baseline test
function testDivideValid() {
  const result = divideNumbers(10, 2);
  if (result !== 5) {
    throw new Error(`Expected 5, got ${result}`);
  }
}

function testParseValid() {
  const result = parseNumericInput(" 42 ");
  if (result !== 42) {
    throw new Error(`Expected 42, got ${result}`);
  }
}

testDivideValid();
testParseValid();
console.log("All baseline tests passed!");
