import { readdirSync, statSync } from "node:fs";
import { basename, join } from "node:path";
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const runIndex = args.indexOf("--run");
const pattern = runIndex >= 0 ? args[runIndex + 1] : "";
const passthrough = runIndex >= 0
  ? args.filter((arg, index) => index !== runIndex && index !== runIndex + 1)
  : args;

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const tests = walk("src").filter((path) => /\.(test|spec)\.ts$/.test(path));
const selected = pattern
  ? tests.filter((path) => basename(path).includes(pattern))
  : tests;

if (!selected.length) {
  console.error(`No test files matched ${pattern || "all tests"}`);
  process.exit(1);
}

const result = spawnSync(
  process.execPath,
  ["--test", ...passthrough, ...selected],
  { stdio: "inherit" },
);

process.exit(result.status ?? 1);
