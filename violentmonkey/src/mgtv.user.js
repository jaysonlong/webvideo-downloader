// ==UserScript==
// @name 芒果TV下载
// @namespace https://github.com/jaysonlong
// @author Jayson Long https://github.com/jaysonlong
// @version 1.0
// @match *://www.mgtv.com/b/*
// @run-at document-start
// @grant none
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/src/mgtv.user.js
// @homepageURL https://github.com/jaysonlong/webvideo-downloader
// ==/UserScript==

var pad = '&nbsp;&nbsp;';

// 保存真实jsonp回调函数
var cbFn = {};

// jsonp拦截
document._createElement = document.createElement;
document.createElement = function(type) {
  var ele = document._createElement(type);
  
  if (type.toLowerCase() == 'script') {
    setTimeout(() => {
      if (ele.src.indexOf('getSource?') > 0) {
        console.log(ele.src);
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

// 获取视频链接
function parseResult(rs) {
  var host = rs.data.stream_domain[0];
  var videoInfo = rs.data.stream.filter(each => each.url != '');
  var tasks = videoInfo.map((each, i) => new Promise(resolve => {
    var {fileformat, name, url} = each;
    var ele = document.createElement('script');
    var cb = 'jaysonCb' + i;
    url = host + each.url + '&callback=' + cb;
    ele.src = url;
    document.body.appendChild(ele);
           
    window[cb] = function(rs) {
      var url = rs.info;
      fetch(url).then(resp => resp.text()).then(rs => {
        var {width, height, size} = parseVideoInfo(rs);
        resolve({
          width, height, size, fileformat, name, url
        });
      });
      
      document.body.removeChild(ele);
      window[cb] = undefined;
    };
  }));
  
  Promise.all(tasks).then(rsList => {
    var html = '';
    rsList.forEach(rs => {
      var {width, height, size, fileformat, name, url} = rs;
      html += `${width + 'x' + height + pad + fileformat + pad + name + pad + size + 'M' + pad}<a href="${url}">右键复制链接地址</a><br><br>`;
    })
    
    openDialog('视频链接', html);
  })
}

// 解析视频信息
function parseVideoInfo(rs) {
  var width = rs.match(/EXT-MGTV-VIDEO-WIDTH:(\d+)/)[1];
  var height = rs.match(/EXT-MGTV-VIDEO-HEIGHT:(\d+)/)[1];
  var size = 0;
  rs.match(/#EXT-MGTV-File-SIZE:\d+/g).forEach(each => {
    var eachSize = parseInt(each.split(':')[1]);
    size += eachSize;
  });
  size = Math.floor(size/1024/1024);
  
  return {
    width, height, size
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
