#!/usr/bin/env node
/*
 * Grab a Douyin video's real play_addr and metadata.
 *
 * Optional env:
 *   VIDEO_URL            required, https://www.douyin.com/video/<aweme_id>
 *   DOUYIN_WORK_DIR      required, output dir for meta.json
 *   DOUYIN_PARSER_JS     optional external parser.js with launchBrowser/applyStealth
 *   NODE_PATH            optional writable node_modules cache
 */
const fs = require('fs');
const path = require('path');

const WORK = process.env.DOUYIN_WORK_DIR;
const VIDEO_URL = process.env.VIDEO_URL;

if (!WORK || !VIDEO_URL) {
  console.error('NEED DOUYIN_WORK_DIR + VIDEO_URL');
  process.exit(2);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function loadParser() {
  const parserPath = process.env.DOUYIN_PARSER_JS;
  if (!parserPath) return null;
  return require(parserPath);
}

async function launchBrowser(parser) {
  if (parser && typeof parser.launchBrowser === 'function') {
    return parser.launchBrowser();
  }
  const puppeteer = require('puppeteer');
  return puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
}

async function applyStealth(parser, page, ua) {
  if (parser && typeof parser.applyStealth === 'function') {
    await parser.applyStealth(page, ua);
    return;
  }
  await page.setUserAgent(ua);
  await page.setViewport({ width: 1365, height: 900 });
}

function findAwemeNode(root) {
  const stack = [root];
  while (stack.length) {
    const node = stack.pop();
    if (!node || typeof node !== 'object') continue;
    if (node.aweme_id && node.video) return node;
    for (const key of Object.keys(node)) stack.push(node[key]);
  }
  return null;
}

function normalizeAweme(videoData) {
  const video = videoData.video || {};
  const playAddr = video.play_addr || {};
  return {
    desc: videoData.desc,
    duration: video.duration,
    play_addr: playAddr.url_list || [],
    ocr: videoData.seo_info && videoData.seo_info.ocr_text,
    caption: video.caption,
    statistics: videoData.statistics,
    aweme_id: videoData.aweme_id,
  };
}

(async () => {
  fs.mkdirSync(WORK, { recursive: true });
  const ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    + '(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36';

  const parser = loadParser();
  const browser = await launchBrowser(parser);
  const page = await browser.newPage();
  await applyStealth(parser, page, ua);

  let videoData = null;
  page.on('response', async (resp) => {
    try {
      const url = resp.url();
      if (url.includes('/aweme/v1/web/aweme/detail') || url.includes('aweme_detail')) {
        const json = await resp.json();
        if (json && json.aweme_detail) videoData = json.aweme_detail;
      }
    } catch (_) {
      // Ignore non-JSON or already-consumed responses.
    }
  });

  await page.goto(VIDEO_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  for (let i = 0; i < 80 && !videoData; i += 1) await sleep(100);

  if (!videoData) {
    try {
      const html = await page.content();
      const match = html.match(/window\._ROUTER_DATA\s*=\s*(.*?);?<\/script>/s);
      if (match) {
        const routerData = JSON.parse(match[1].trim().replace(/;$/, ''));
        videoData = findAwemeNode(routerData);
      }
    } catch (_) {
      // Keep NO_DATA failure below.
    }
  }

  await browser.close();
  if (!videoData) {
    console.error('NO_DATA');
    process.exit(3);
  }

  const out = normalizeAweme(videoData);
  fs.writeFileSync(path.join(WORK, 'meta.json'), JSON.stringify(out, null, 2));
  console.log('DURATION', out.duration || 'UNKNOWN');
  console.log('PLAY', (out.play_addr || [])[0] || 'NONE');
})();

