import { applyDiscount, parseNumericInput } from "./calculator";

// Reproduction test 1: null input triggers TypeError
try {
  parseNumericInput(null);
  console.error("FAIL: Expected TypeError on null input");
} catch (e) {
  console.log("PASS: Caught expected error on null input:", (e as Error).message);
}

// Reproduction test 2: discount logic error (adds instead of subtracts)
const discounted = applyDiscount(100, 20);
if (discounted === 120) {
  console.log("CONFIRMED BUG: applyDiscount returned 120 instead of 80");
}
