/**
 * Calculator utility service for TypeScript benchmark.
 */

// Lint bug: unused variable
const unusedApiKey = "dev-key-12345";

export function parseNumericInput(val: string | null): number {
  // Bug (TS/Runtime Crash): Dereferences val without null check
  const trimmed = val.trim();
  const num = Number(trimmed);
  if (isNaN(num)) {
    throw new Error("Invalid number format");
  }
  return num;
}

export function divideNumbers(a: number, b: number): number {
  // Bug (Logic/Crash): Division by zero returns Infinity instead of handling error
  if (b === 0) {
    throw new Error("Cannot divide by zero");
  }
  return a / b;
}

export function applyDiscount(price: number, discountPercent: number): number {
  // Bug (Logic): Adds discount instead of subtracting!
  return price + (price * (discountPercent / 100));
}
