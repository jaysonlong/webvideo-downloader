// ==UserScript==
// @name 爱奇艺视频下载
// @namespace Violentmonkey Scripts
// @author     JaysonLong https://github.com/jaysonlong
// @match *://www.iqiyi.com/*.html
// @require https://cdn.bootcdn.net/ajax/libs/jquery/1.7.2/jquery.min.js
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @run-at document-start
// @grant none
// ==/UserScript==

var pad = '&nbsp;&nbsp;';

// 保存真实jsonp回调函数
var cbFn = {};

// 方法1，ajax拦截
ah.hook({
  open: function(args,xhr){
    var url = args[1];
    if (url.indexOf('dash?') > 0) {
      parseUrl(url);
    }
  }
});

// 方法2，jsonp拦截
document._createElement = document.createElement;
document.createElement = function(type) {
  var ele = document._createElement(type);
  
  if (type.toLowerCase() == 'script') {
    setTimeout(() => {
      if (ele.src.indexOf('/jp/dash?') > 0) {
        var jsonpCbName = ele.src.split(/\?|&/).filter(each => each.startsWith('callback='))[0].substring(9);
        
        if (!cbFn[jsonpCbName]) {
          cbFn[jsonpCbName] = window[jsonpCbName];
          Object.defineProperty(window, jsonpCbName, {
            get: ()=>{
              if (!cbFn[jsonpCbName]) {
                return undefined;
              }
              return (rs) => {
                try{
                  parseResult(rs);
                } catch(e) {}
                cbFn[jsonpCbName](rs);
              };
            },
            set: (fn)=>{
              cbFn[jsonpCbName] = fn;
            }
          });
        }
      }
    }, 10);
  }
  
  return ele;
}

// 获取m3u8链接
function parseUrl(url) {
  fetch(url, {credentials: 'include'}).then(response => response.json()).then(rs => {
    console.log(rs);
    
    var videos = rs.data.program.video.filter(each => each.m3u8 != undefined);
    if (videos.length) {
      var {vsize:size, m3u8, ff:fileformat, scrsz:wh, vid} = videos[0];
      var blob = new Blob([m3u8]);
      var blobUrl = URL.createObjectURL(blob);
      var size = Math.floor(size / 1024 / 1024);
      var html = `${fileformat + pad + wh + pad + size + 'M' + pad}<a href="${url}">右键复制链接地址</a>` 
        + `${pad + '或' + pad}<a download="${vid}.m3u8" href="${blobUrl}">点击下载m3u8文件</a><br>`;
      openDialog('视频链接', html);
    }
  });
};

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
