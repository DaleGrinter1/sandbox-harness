#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
const activeRoot = path.join(root, "docs", "exec-plans", "active");

const requiredSections = [
  "## Purpose / Big Picture",
  "## Surprises & Discoveries",
  "## Decision Log",
  "## Outcomes & Retrospective",
  "## Context and Orientation",
  "## Plan of Work",
  "## Concrete Steps",
  "## Machine State",
  "## Progress",
  "## Testing Approach",
  "## Constraints & Considerations",
];

const errors = [];

function exists(filePath) {
  return fs.existsSync(filePath);
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    errors.push(`${relative(filePath)} is not valid JSON: ${error.message}`);
    return null;
  }
}

function relative(filePath) {
  return path.relative(root, filePath) || ".";
}

function listDirs(dirPath) {
  if (!exists(dirPath)) return [];
  return fs
    .readdirSync(dirPath, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(dirPath, entry.name));
}

function walk(dirPath, visit) {
  if (!exists(dirPath)) return;
  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    const entryPath = path.join(dirPath, entry.name);
    visit(entryPath, entry);
    if (entry.isDirectory()) walk(entryPath, visit);
  }
}

if (!exists(activeRoot)) {
  errors.push("docs/exec-plans/active is missing");
} else {
  walk(activeRoot, (entryPath, entry) => {
    if (entry.isDirectory() && entry.name === "tasks") {
      errors.push(`${relative(entryPath)} is deprecated; use state/feature-list.json instead`);
    }
    if (entry.isFile() && entry.name.toLowerCase().endsWith(".md") && entry.name !== "README.md") {
      const parent = path.basename(path.dirname(entryPath));
      if (!entry.name.startsWith("PLAN_") || parent === "active") {
        errors.push(`${relative(entryPath)} is not an allowed active markdown task/plan file`);
      }
    }
  });
}

for (const initiativeDir of listDirs(activeRoot)) {
  const initiative = path.basename(initiativeDir);
  const planFiles = fs.readdirSync(initiativeDir).filter((name) => /^PLAN_.+\.md$/.test(name));
  if (planFiles.length !== 1) {
    errors.push(`${relative(initiativeDir)} must contain exactly one PLAN_*.md file`);
    continue;
  }

  const planPath = path.join(initiativeDir, planFiles[0]);
  const planText = fs.readFileSync(planPath, "utf8");
  for (const section of requiredSections) {
    if (!planText.includes(section)) {
      errors.push(`${relative(planPath)} is missing section ${section}`);
    }
  }

  const stateDir = path.join(initiativeDir, "state");
  const featurePath = path.join(stateDir, "feature-list.json");
  const sessionPath = path.join(stateDir, "session-state.json");
  const progressPath = path.join(stateDir, "progress.jsonl");

  for (const requiredPath of [featurePath, sessionPath, progressPath]) {
    if (!exists(requiredPath)) errors.push(`${relative(requiredPath)} is missing`);
  }

  const featureList = exists(featurePath) ? readJson(featurePath) : null;
  const sessionState = exists(sessionPath) ? readJson(sessionPath) : null;
  const featureIds = new Set();

  if (featureList) {
    if (featureList.initiative !== initiative) {
      errors.push(`${relative(featurePath)} initiative must be ${initiative}`);
    }
    if (!Array.isArray(featureList.features) || featureList.features.length === 0) {
      errors.push(`${relative(featurePath)} must contain a non-empty features array`);
    } else {
      for (const feature of featureList.features) {
        if (!feature || typeof feature !== "object") {
          errors.push(`${relative(featurePath)} contains a non-object feature`);
          continue;
        }
        if (typeof feature.id !== "string" || feature.id.length === 0) {
          errors.push(`${relative(featurePath)} contains a feature without a string id`);
        } else if (featureIds.has(feature.id)) {
          errors.push(`${relative(featurePath)} contains duplicate feature id ${feature.id}`);
        } else {
          featureIds.add(feature.id);
        }
        if (typeof feature.title !== "string" || feature.title.length === 0) {
          errors.push(`${relative(featurePath)} feature ${feature.id ?? "<unknown>"} needs a title`);
        }
        if (typeof feature.passes !== "boolean") {
          errors.push(`${relative(featurePath)} feature ${feature.id ?? "<unknown>"} must have boolean passes`);
        }
      }
    }
  }

  if (sessionState) {
    if (sessionState.initiative !== initiative) {
      errors.push(`${relative(sessionPath)} initiative must be ${initiative}`);
    }
    if (typeof sessionState.active_feature !== "string") {
      errors.push(`${relative(sessionPath)} active_feature must be a string`);
    } else if (featureIds.size > 0 && !featureIds.has(sessionState.active_feature)) {
      errors.push(`${relative(sessionPath)} active_feature ${sessionState.active_feature} is not in feature-list.json`);
    }
    if (!Array.isArray(sessionState.blockers)) {
      errors.push(`${relative(sessionPath)} blockers must be an array`);
    }
    if (typeof sessionState.next_action !== "string" || sessionState.next_action.length === 0) {
      errors.push(`${relative(sessionPath)} next_action must be a non-empty string`);
    }
    if (!Array.isArray(sessionState.handoff_rules) || sessionState.handoff_rules.length === 0) {
      errors.push(`${relative(sessionPath)} handoff_rules must be a non-empty array`);
    }
  }

  if (exists(progressPath)) {
    const lines = fs.readFileSync(progressPath, "utf8").split(/\r?\n/).filter(Boolean);
    if (lines.length === 0) {
      errors.push(`${relative(progressPath)} must contain at least one JSONL entry`);
    }
    lines.forEach((line, index) => {
      let entry;
      try {
        entry = JSON.parse(line);
      } catch (error) {
        errors.push(`${relative(progressPath)} line ${index + 1} is not valid JSON: ${error.message}`);
        return;
      }
      for (const key of ["timestamp", "actor", "type", "summary"]) {
        if (typeof entry[key] !== "string" || entry[key].length === 0) {
          errors.push(`${relative(progressPath)} line ${index + 1} missing string ${key}`);
        }
      }
      if (Number.isNaN(Date.parse(entry.timestamp))) {
        errors.push(`${relative(progressPath)} line ${index + 1} timestamp is invalid`);
      }
      if (entry.feature_id !== undefined && !featureIds.has(entry.feature_id)) {
        errors.push(`${relative(progressPath)} line ${index + 1} references unknown feature ${entry.feature_id}`);
      }
      if (!Array.isArray(entry.evidence)) {
        errors.push(`${relative(progressPath)} line ${index + 1} evidence must be an array`);
      }
    });
  }
}

if (errors.length > 0) {
  console.error("execplan validation failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("execplan validation passed");
