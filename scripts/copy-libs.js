#!/usr/bin/env node

/**
 * WozapAuto Library Copier
 * Copies npm packages to Django static folders
 */

const fs = require('fs');
const path = require('path');

// Configuration
const config = {
  staticDir: 'static',
  jsLibsDir: 'static/js/libs',
  cssLibsDir: 'static/css/libs',
  fontsDir: 'static/fonts',
  nodeModulesDir: 'node_modules'
};

// Ensure directories exist
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`📁 Created directory: ${dir}`);
  }
}

// Copy files matching pattern
function copyFiles(sourceDir, targetDir, pattern) {
  if (!fs.existsSync(sourceDir)) {
    console.log(`⚠️  Source directory not found: ${sourceDir}`);
    return;
  }

  ensureDir(targetDir);
  
  const files = findFiles(sourceDir, pattern);
  
  files.forEach(file => {
    const relativePath = path.relative(sourceDir, file);
    const targetPath = path.join(targetDir, path.basename(file));
    
    try {
      fs.copyFileSync(file, targetPath);
      console.log(`✅ Copied: ${relativePath} → ${path.relative(process.cwd(), targetPath)}`);
    } catch (error) {
      console.error(`❌ Failed to copy ${file}:`, error.message);
    }
  });
}

// Find files recursively
function findFiles(dir, pattern) {
  let results = [];
  
  if (!fs.existsSync(dir)) return results;
  
  const list = fs.readdirSync(dir);
  
  list.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      results = results.concat(findFiles(filePath, pattern));
    } else if (pattern.test(file)) {
      results.push(filePath);
    }
  });
  
  return results;
}

// Main execution
console.log('🚀 WozapAuto Library Copier');
console.log('============================');

// Ensure target directories exist
ensureDir(config.jsLibsDir);
ensureDir(config.cssLibsDir);
ensureDir(config.fontsDir);

// Copy JavaScript files
console.log('\n📦 Copying JavaScript libraries...');
copyFiles(config.nodeModulesDir, config.jsLibsDir, /\.(min\.)?js$/);

// Copy CSS files
console.log('\n🎨 Copying CSS libraries...');
copyFiles(config.nodeModulesDir, config.cssLibsDir, /\.(min\.)?css$/);

// Copy font files
console.log('\n🔤 Copying font files...');
copyFiles(config.nodeModulesDir, config.fontsDir, /\.(woff2?|ttf|eot|svg)$/);

console.log('\n✅ Library copying complete!');
console.log(`📁 JavaScript: ${config.jsLibsDir}`);
console.log(`🎨 CSS: ${config.cssLibsDir}`);
console.log(`🔤 Fonts: ${config.fontsDir}`);

// List copied files
console.log('\n📋 Copied files:');
['js', 'css', 'fonts'].forEach(type => {
  const dir = `static/${type}/libs`;
  if (fs.existsSync(dir)) {
    const files = fs.readdirSync(dir);
    if (files.length > 0) {
      console.log(`\n${type.toUpperCase()}:`);
      files.forEach(file => console.log(`  - ${file}`));
    }
  }
});
