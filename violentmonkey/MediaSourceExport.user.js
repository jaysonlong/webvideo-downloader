// ==UserScript==
// @name MSE视频导出（实验）
// @namespace https://github.com/jaysonlong
// @author Jayson Long https://github.com/jaysonlong
// @version 1.0
// @match *://*/*
// @require https://cdn.bootcdn.net/ajax/libs/jquery/1.7.2/jquery.min.js
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @grant none
// @run-at document-start
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/MediaSourceExport.user.js
// @homepageURL https://github.com/jaysonlong/webvideo-downloader
// ==/UserScript==

var pad = '&nbsp;&nbsp;';
var serverUrl = 'ws://127.0.0.1:18888';
var videoEle = null;
var ws = null;
storage = {
  audio: {},
  video: {},
  lastPoint: -1,
  endPoint: 0,
  needPlay: false,
  inTransit: false,
  seekInter: 0,
  seekInterTime: 500,
  sendInter: 0,
  sendInterTime: 1000,
}

function seekLastPost() {
  if (!storage.inTransit || videoEle.buffered.length == 0) {
    return;
  }

  storage.needPlay || videoEle.paused || videoEle.pause();
  storage.endPoint = parseInt(videoEle.buffered.end(0));

  if (storage.endPoint != storage.lastPoint) {
    videoEle.currentTime = storage.lastPoint = storage.endPoint;
  } else if (Math.abs(storage.endPoint - videoEle.duration) < 3) {
      stopFetch();
  }
}

function sendData() {
  function doSend(type) {
    var target = storage[type], bufferArr = target.bufferArr;
    if (!bufferArr.length) return;

    if (target.isFmp4 && bufferArr.slice(-1)[0].toBoxes().pop().type != 'mdat') {
      target.bufferArr = [bufferArr.pop()];
      if (!bufferArr.length) return;
    } else {
      target.bufferArr = [];
    }

    var realData = bufferArr.map(each => each.splitInitSeg()[1]);
    if (!target.initSegSent) {
      realData.unshift(target.initSeg);
      target.initSegSent = true;
    }
    var desc = JSON.stringify({
      type: type,
      endPoint: storage.endPoint,
    });
    ws.send(new Blob([desc, '\r\n', ...realData]));
    var hashes = realData.map(each => each.hash());
    target.sentArr.push(...hashes);

    if (target.isFmp4) {
      var boxTypes = realData.map(each => each.toBoxes().map(e => e.type));
      console.log(type, boxTypes.reduce((a, b) => (a.length && a.push('|'), a.concat(b)), []));
    } else {
      console.log(type, realData.map(each => each.byteLength))
    }
  }

  if (!storage.inTransit) return;
  doSend('audio');
  doSend('video');
}

function startFetch(e) {
  e && e.preventDefault();
  if (ws && ws.readyState <= 1) {
    ws.close();
  }

  ws = new WebSocket(serverUrl);
  ws.onerror = function() {
    alert('请先运行 "python daemon.py"');
  };
  ws.onopen = function() {
    videoEle = $('video')[0];
    videoEle.pause();
    
    var fileName = prompt('输入文件名: ', document.title);
    if (fileName == null) {
      return;
    }
    var startTime = prompt(`输入起始时间（秒），共${parseInt(videoEle.duration)}秒: `, '0');
    if (startTime == null) {
      return;
    }
    if ((startTime = parseFloat(startTime)) == NaN) {
      alert('时间格式应为数字');
      return;
    }
    
    videoEle._volume = videoEle.volume;
    videoEle.volume = 0;
    var {audio, video} = storage;
    ws.send(JSON.stringify({
      type: 'stream',
      fileName: fileName,
      audioFormat: '.' + audio.format,
      videoFormat: '.' + video.format,
      startTime: startTime,
      duration: parseInt(videoEle.duration),
    }));
    
    var inter = setInterval(() => {
      var now = new Date().getTime();
      var diff = now - Math.min(audio.lastAppendTime, video.lastAppendTime);
      if (!audio.sb.updating && !video.sb.updating && diff >= 500) {
        clearInterval(inter);
        
        storage.inTransit = true;
        audio.initSegSent = false;
        video.initSegSent = false;
        videoEle.currentTime = startTime;
        audio.sb && audio.sb.remove(0, audio.sb.buffered.end(audio.sb.buffered.length-1));
        video.sb && video.sb.remove(0, video.sb.buffered.end(video.sb.buffered.length-1));
        
        videoEle.addEventListener("canplay", () => {
          storage.seekInter = setInterval(seekLastPost, storage.seekInterTime);
          storage.sendInter = setInterval(sendData, storage.sendInterTime);
          storage.needPlay && videoEle.play();
        }, {once: true});
        videoEle.addEventListener("ended", stopFetch);
      }
    }, 500);
  };
  ws.addEventListener('close', stopFetch, {once: true});
}

function stopFetch(e) {
  e && e.preventDefault();
  videoEle.pause();
  videoEle.volume = videoEle._volume;
  clearInterval(storage.seekInter);
  
  setTimeout(() => {
    storage.inTransit = false;
    clearInterval(storage.sendInter);
    if (ws.readyState > 1) return;

    var desc = JSON.stringify({
      type: 'finish',
    });
    ws.send(desc + '\r\n');
    ws.close();
    ws.addEventListener('close', () => alert('已完成'), {once: true});
  }, storage.sendInterTime + 200);
}

MediaSource.prototype.addSourceBuffer = new Proxy(MediaSource.prototype.addSourceBuffer, {
  apply: function(fn, thisArg, [mimeType]) {
    var sb = fn.apply(thisArg, [mimeType]);;
    var rs = mimeType.match(/(\w+)\/(\w+); *codecs="?(.+)"?/);
    var [_, type, format, codecs] = rs;
    if (codecs.includes('mp4a') && type != 'audio') {
      mimeType = mimeType.replace(type, 'audio');
      type = 'audio';
    }

    var target = storage[type];
    target.sb = sb;
    if (!target.format) {
      target.format = format;
      target.mimeType = mimeType;
      target.isFmp4 = format == 'mp4';
      target.bufferArr = [];
      target.sentArr = [];
      target.hashArr = [];
      target.dataArr = [];

      if (storage.audio.format && storage.video.format) {
        var htmls = [];
        htmls.push(`音频${pad + storage.audio.mimeType}`);
        htmls.push(`视频${pad + storage.video.mimeType}`);
        htmls.push('<a class="start">点击开始导出(页面不可关闭)</a>'
          + pad + pad + '<a class="stop">点击停止导出</a>');
        var html = htmls.join('<br><br>');
        openDialog('MSE视频流导出', html, {
          'start': startFetch,
          'stop': stopFetch,
        });
      }
    }
    sb.type = type;
    return sb;
  }
});

SourceBuffer.prototype.appendBuffer = new Proxy(SourceBuffer.prototype.appendBuffer, {
  apply: function(fn, thisArg, [buffer]) {
    fn.apply(thisArg, [buffer]);

    var target = storage[thisArg.type];
    buffer = buffer instanceof ArrayBuffer ? buffer : buffer.buffer;
    buffer.isFmp4 = target.isFmp4;

    var hash = buffer.hash();
    target.hashArr.push(buffer.hash());
    // target.dataArr.push(buffer);
    // console.log('appendInterval', thisArg.type);
    target.lastAppendTime = new Date().getTime();

    if (!target.initSeg) {
      target.initSeg = buffer.splitInitSeg()[0];
      target.initSegHash = target.initSeg.hash();
      return;
    }
    if (storage.inTransit) {
      if (hash != target.initSegHash && !target.sentArr.slice(-4).includes(hash)) {
        target.bufferArr.push(buffer);
      }
    }
  }
});

function openDialog(title, html, onClicks) {
  var div = $(`<div style="">${title + pad}<button class="remove">关闭</button><br><br>${html}</div>`);
  div[0].setAttribute('style', 'font-size:15px;position:absolute;width:50%;padding:25px;border:2px solid #03a9f4;' +
    'border-radius:10px;background:rgba(255,255,255,.9);top:100px;left:20%;z-index:10000;word-wrap:break-word;');
  $('body').append(div);

  div.find('a').css('color', '#0000EE');
  Object.keys(onClicks).forEach(clz => {
    div.find('a.' + clz).click(onClicks[clz]);
  })
  div.find('button.remove').css('marginLeft', '20px').click((e) => {
    div.remove();
    e.stopPropagation();
  });
};

Uint8Array.prototype.hash = function() {
  var hcode = 1315423911;
  this.forEach(v => {
    hcode ^= (hcode << 5) + (hcode >> 2)  + v;
  });
  return this.length + ' | ' + (hcode & 0x7FFFFFFF);
}

Uint8Array.prototype.toBoxes = function() {
  if (!this.buffer.isFmp4) {
    return false;
  }

  var boxes = [], currSize = 0;
  var dataView = new DataView(this.buffer, this.byteOffset);

  while (currSize < this.length) {
    var boxSize = dataView.getUint32(currSize); 
    var boxType = String.fromCharCode(...this.subarray(currSize + 4, currSize + 8));
    currSize += boxSize;
    boxes.push({
      size: boxSize,
      type: boxType,
    });
  }
  return boxes;
}

Uint8Array.prototype.splitInitSeg = function() {
  if (!this.buffer.isFmp4) {
    return [this, this];
  }

  var initSegSize = 0;
  this.toBoxes().every(box => {
    if (box.type == 'ftyp' || box.type == 'moov') {
      initSegSize += box.size;
      return true;
    }
  })
  var initSeg = this.subarray(0, initSegSize);
  var dataSeg = this.subarray(initSegSize);
  return [initSeg, dataSeg];
}

ArrayBuffer.prototype.hash = function() {
  return new Uint8Array(this).hash();
}

ArrayBuffer.prototype.toBoxes = function() {
  return new Uint8Array(this).toBoxes();
}

ArrayBuffer.prototype.splitInitSeg = function() {
  return new Uint8Array(this).splitInitSeg();
}