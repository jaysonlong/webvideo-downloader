// ==UserScript==
// @name 腾讯视频下载
// @namespace Violentmonkey Scripts
// @author JaysonLong https://github.com/jaysonlong/webvideo-downloader
// @version 1.0
// @match *://v.qq.com/x/cover/*
// @match *://v.qq.com/x/page/*
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @run-at document-start
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/腾讯视频下载.user.js
// @grant none
// ==/UserScript==

var pad = '&nbsp;&nbsp;';

// 仅处理一次，避免切换清晰度时再次触发
var handled = false;
var params = {};

// ajax拦截
ah.hook({
  // 绑定url供send回调获取
  open: (args, xhr) => {
    var [method, url] = args;
    if (url.indexOf('qq.com/proxyhttp') > 0) {
      xhr.method = method.toUpperCase();
      xhr.url = url;
    }
  },
  // 绑定isVinfo供onreadystatechange回调获取
  send: (args, xhr) => {
    var body = args[0];
    if (xhr.url && body.indexOf('vinfoparam') > 0) {
      xhr.isVinfo = true;
      var currDef = body.match(/defn=([^& ]*)/)[1];
      params = {
        url: xhr.url,
        method: xhr.method,
        body: body,
        currDef: currDef,
      };
    }
  },
  onreadystatechange: function(xhr) {
    if (!handled && xhr.isVinfo && xhr.readyState == 4) {
      handled = true;
      parseResult(xhr.responseText);
    }
  },
});

// 获取视频链接
function parseResult(rs) {
  var data = typeof rs == "string" ? JSON.parse(rs) : rs;
  var vinfo = JSON.parse(data.vinfo);
  
  console.log(vinfo);
  
  var tasks = vinfo.fl.fi.map(each => new Promise(resolve => {
    var {name:defn, cname:defdesc} = each;
    var body = params.body.replace('defn=' + params.currDef, 'defn=' + defn);
    fetch(params.url, {
      body: body,
      method: params.method,
    })
      .then(resp => resp.json())
      .then(data => ({
        defdesc, data
      }))
      .then(resolve);
  }));
  
  Promise.all(tasks).then(rsList => {
    var html = '';
    rsList.forEach(each => {
      try {
        var {url, width, height, size} = parseVideoInfo(each.data);
        html += `${width + 'x' + height + pad + each.defdesc + pad + size + 'M' + pad}<a href="${url}">右键复制链接地址</a><br/><br/>`;
      } catch (e) {}
    })
    
    openDialog('视频链接', html);
  });
}

// 解析视频信息对象
function parseVideoInfo(data) {
  var vinfo = JSON.parse(data.vinfo);
  var vi = vinfo.vl.vi[0];
  var ui = vi.ul.ui[0];
  var url = ui.url;
  var {vw:width, vh:height, fs:size} = vi;
  size = Math.floor(size / 1024 / 1024);
  
  return {
    url, width, height, size
  }
}

function openDialog(title, html) {
  var div = $(`<div style="">${title + pad}<button class="remove">关闭</button><br><br>${html}</div>`);
  div[0].setAttribute('style', 'font-size:15px;position:absolute;width:60%;padding:25px;border:2px solid #03a9f4;'
    + 'border-radius:10px;background:rgba(255,255,255,.9);top:7%;left:15%;z-index:10000;word-wrap:break-word;');
  
  $('body').append(div);
  div.find('a').css('color', '#0000EE');
  div.find('button.remove').css('marginLeft', '20px').click((e) => {
    div.remove();
    e.stopPropagation();
  });
};

// 检测url变化
window.history._pushState = window.history.pushState;
window.history._replaceState = window.history.replaceState;
window.history.pushState = function() {
  handled = false;
  return window.history._pushState(...arguments);
}
window.history.replaceState = function() {
  handled = false;
  return window.history._replaceState(...arguments);
}
