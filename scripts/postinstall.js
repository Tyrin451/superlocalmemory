#!/usr/bin/env node
/**
 * SuperLocalMemory V3 - NPM Postinstall Script
 *
 * Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
 * Licensed under MIT License
 * Repository: https://github.com/qualixar/superlocalmemory
 */

const path = require('path');
const os = require('os');
const fs = require('fs');

console.log('\n════════════════════════════════════════════════════════════');
console.log('  SuperLocalMemory V3 - Post-Installation');
console.log('  by Varun Pratap Bhardwaj / Qualixar');
console.log('  https://github.com/qualixar/superlocalmemory');
console.log('════════════════════════════════════════════════════════════\n');

// V3 data directory
const SLM_HOME = path.join(os.homedir(), '.superlocalmemory');
const V2_HOME = path.join(os.homedir(), '.claude-memory');

// Ensure V3 data directory exists
if (!fs.existsSync(SLM_HOME)) {
    fs.mkdirSync(SLM_HOME, { recursive: true });
    console.log('✓ Created data directory: ' + SLM_HOME);
} else {
    console.log('✓ Data directory exists: ' + SLM_HOME);
}

// Detect V2 installation
if (fs.existsSync(V2_HOME) && fs.existsSync(path.join(V2_HOME, 'memory.db'))) {
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════╗');
    console.log('║  V2 Installation Detected                                ║');
    console.log('╚══════════════════════════════════════════════════════════╝');
    console.log('');
    console.log('  Found V2 data at: ' + V2_HOME);
    console.log('  Your memories are safe and will NOT be deleted.');
    console.log('');
    console.log('  To migrate V2 data to V3, run:');
    console.log('    slm migrate');
    console.log('');
    console.log('  Read the migration guide:');
    console.log('    https://github.com/qualixar/superlocalmemory/wiki/Migration-from-V2');
    console.log('');
}

console.log('════════════════════════════════════════════════════════════');
console.log('  ✓ SuperLocalMemory V3 installed successfully!');
console.log('');
console.log('  Quick start:');
console.log('    slm setup          # First-time configuration');
console.log('    slm status         # Check system status');
console.log('    slm remember "..." # Store a memory');
console.log('    slm recall "..."   # Search memories');
console.log('');
console.log('  Documentation: https://github.com/qualixar/superlocalmemory/wiki');
console.log('════════════════════════════════════════════════════════════\n');
