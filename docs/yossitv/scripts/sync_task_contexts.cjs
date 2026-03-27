#!/usr/bin/env node
"use strict";

const path = require("path");
const { spawnSync } = require("child_process");

function main() {
  const python = process.env.PYTHON || "python";
  const script = path.resolve(__dirname, "../render_task_views.py");
  const target = process.argv[2] || path.resolve(__dirname, "..");
  const result = spawnSync(python, [script, target], { stdio: "inherit" });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status === null ? 1 : result.status);
}

main();
