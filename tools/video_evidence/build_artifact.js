#!/usr/bin/env node
/*
 * Build a JuryPersonas short-video artifact from realframe pipeline outputs.
 *
 * The script does not describe images. It only records real frame file paths.
 * Provide --descriptions with multimodal/agent-reviewed descriptions when
 * available.
 */
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith('--')) continue;
    const name = key.slice(2);
    const value = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    args[name] = value;
  }
  return args;
}

function readJsonIfExists(filePath, fallback) {
  if (!filePath || !fs.existsSync(filePath)) return fallback;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readTextIfExists(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return '';
  return fs.readFileSync(filePath, 'utf8').trim();
}

function durationSeconds(raw) {
  if (raw == null) return undefined;
  const value = Number(raw);
  if (!Number.isFinite(value)) return undefined;
  return value > 1000 ? Math.round(value / 1000) : value;
}

function numericFrameIndex(name) {
  const match = name.match(/(\d+)(?=\.(jpe?g|png)$)/i);
  return match ? Number(match[1]) : Number.POSITIVE_INFINITY;
}

function loadDescriptions(filePath) {
  const raw = readJsonIfExists(filePath, {});
  if (Array.isArray(raw)) {
    const out = {};
    for (const item of raw) {
      if (!item || typeof item !== 'object') continue;
      if (item.file) out[item.file] = item.description || item.visual || '';
      if (item.image) out[path.basename(item.image)] = item.description || item.visual || '';
      if (item.ts_sec != null) out[String(item.ts_sec)] = item.description || item.visual || '';
    }
    return out;
  }
  return raw && typeof raw === 'object' ? raw : {};
}

function descriptionFor(desc, baseName, tsSec) {
  return desc[baseName] || desc[String(tsSec)] || '';
}

function main() {
  const args = parseArgs(process.argv);
  const work = path.resolve(args.work || process.env.WORK || process.cwd());
  const outPath = path.resolve(args.out || path.join(work, 'artifact.realframe.json'));
  const frameInterval = Number(args['frame-interval'] || process.env.FRAME_INTERVAL || 3);
  const meta = readJsonIfExists(path.join(work, 'meta.json'), {});
  const transcript = readTextIfExists(path.join(work, 'transcript.txt'));
  const desc = loadDescriptions(args.descriptions);
  const framesDir = path.join(work, 'frames');
  const frameNames = fs.existsSync(framesDir)
    ? fs.readdirSync(framesDir)
      .filter((name) => /\.(jpe?g|png)$/i.test(name))
      .sort((a, b) => numericFrameIndex(a) - numericFrameIndex(b) || a.localeCompare(b))
    : [];

  const keyFrames = frameNames.map((name) => {
    const index = numericFrameIndex(name);
    const tsSec = Number.isFinite(index) ? Math.max(index - 1, 0) * frameInterval : null;
    const imagePath = path.join(framesDir, name);
    const description = descriptionFor(desc, name, tsSec);
    return {
      ts_sec: tsSec,
      image: imagePath,
      image_path: imagePath,
      description,
      observed: true,
      source: 'realframe_pipeline:ffmpeg',
      needs_visual_description: !description,
    };
  });

  const artifact = {
    artifact_type: '短视频',
    artifact_locator: process.env.VIDEO_URL || meta.aweme_id || outPath,
    title: meta.desc || '抖音真实抽帧视频',
    duration_sec: durationSeconds(meta.duration),
    platform: '抖音',
    url: process.env.VIDEO_URL,
    key_frames: keyFrames,
    transcript,
    captions: meta.ocr || meta.caption || '',
    statistics: meta.statistics || {},
    evidence_boundary: {
      source: 'realframe_pipeline',
      video_downloaded: fs.existsSync(path.join(work, 'video.mp4')),
      frames_observed: true,
      visual_descriptions_required: keyFrames.some((frame) => frame.needs_visual_description),
      no_inferred_frames: true,
    },
  };

  fs.writeFileSync(outPath, `${JSON.stringify(artifact, null, 2)}\n`);
  console.log(`artifact -> ${outPath}`);
  console.log(`frames=${keyFrames.length} needs_visual_description=${keyFrames.filter((f) => f.needs_visual_description).length}`);
}

main();

