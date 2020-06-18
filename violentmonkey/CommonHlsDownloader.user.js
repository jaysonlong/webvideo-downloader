// ==UserScript==
// @name 通用hls下载器
// @namespace https://github.com/jaysonlong
// @author Jayson Long https://github.com/jaysonlong
// @version 1.0
// @exclude-match *://www.bilibili.com/*/play/*
// @exclude-match *://www.bilibili.com/video/*
// @exclude-match *://www.iqiyi.com/*.html
// @exclude-match *://v.qq.com/x/cover/*
// @exclude-match *://v.qq.com/x/page/*
// @exclude-match *://www.mgtv.com/b/*
// @require https://cdn.bootcdn.net/ajax/libs/jquery/1.7.2/jquery.min.js
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @grant none
// @run-at document-start
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/CommonHlsDownloader.user.js
// @homepageURL https://github.com/jaysonlong/webvideo-downloader
// ==/UserScript==


var pad = '&nbsp;&nbsp;';
var serverUrl = 'ws://127.0.0.1:18888';

console._log = console.log;
// ajax拦截
ah.hook({
  open: function(args, xhr) {
    var url = args[1];
    if (url.indexOf('.m3u8') > -1) {
      console._log(url);
      var html = `<a class="remote" href="${url}">点击下载或复制链接</a>`;
      openDialog(`hls链接`, html);
    }
  },
});

function openDialog(title, html) {
  var div = $(`<div style="">${title + pad}<button class="remove">关闭</button><br><br>${html}</div>`);
  div[0].setAttribute('style', 'font-size:15px;position:absolute;width:50%;padding:25px;border:2px solid #03a9f4;' +
    'border-radius:10px;background:rgba(255,255,255,.9);top:100px;left:20%;z-index:10000;word-wrap:break-word;');
  $('body').append(div);

  div.find('a').css('color', '#0000EE');
  div.find('a.remote').click(remoteCall);
  div.find('button.remove').css('marginLeft', '20px').click((e) => {
    div.remove();
    e.stopPropagation();
  });
};


async function remoteCall(e) {
  e.preventDefault();
  var ws = new WebSocket(serverUrl);
  var dom = this;

  ws.onerror = function() {
    alert('请先运行 "python daemon.py"');
  };
  ws.onopen = function() {
    var payload = {
      fileName: prompt('输入文件名: ', document.title)
    };
    if (payload.fileName == null) {
      return;
    }

    payload.linksurl = dom.href;
    payload.type = 'link';
    if (dom.dataset.multi && !(payload.pRange = prompt('输入首、尾P(空格分隔)或单P: '))) {
      return;
    }
    ws.send(JSON.stringify(payload));
    ws.close();
  };
}
