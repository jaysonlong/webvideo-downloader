// ==UserScript==
// @name B站视频下载
// @namespace Violentmonkey Scripts
// @author     JaysonLong https://github.com/jaysonlong
// @match *://www.bilibili.com/*/play/*
// @match *://www.bilibili.com/video/*
// @require https://cdn.bootcdn.net/ajax/libs/jquery/1.7.2/jquery.min.js
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @run-at document-start
// @grant none
// ==/UserScript==

var pad = '&nbsp;&nbsp;';

// 仅处理一次，避免视频看完后预加载其他视频信息时再次触发
var handled = false;
var playinfoSource = "";
var playinfoUrl = "";

// 方法1，从html script标签中获取playinfo
$(() => {
  if (!handled && $('html').html().includes('__playinfo__')) {
    handled = true;
    playinfoSource = "embedded html";
    
    eval($('script:contains(__playinfo__)').text());
    parseData(window.__playinfo__.data);
  }
});

// 方法2，拦截ajax请求获取playinfo
ah.hook({
  open: function(args, xhr) {
    var url = args[1];
    if (!handled && url.indexOf('playurl?') > 0) {
      console.log(playinfoUrl);
      
      handled = true;
      playinfoSource = "xhr request";
      playinfoUrl = url.startsWith('http') ? url : window.location.protocol + url;
      
      fetch(playinfoUrl, {credentials: 'include'}).then(response => response.json()).then(rs => {
        parseData(rs.result || rs.data);
      });
    }
  }
});

// 获取视频链接
function parseData(data) {
  console.log(data);
  
  if (data.dash) {
    var { duration, audio: audios, video: videos } = data.dash;
    var sortBw = function (a, b) { return b.bandwidth - a.bandwidth}
    audios.sort(sortBw);
    var { baseUrl: audioUrl, bandwidth: audioBw } = audios[0];

    var html = '<b>单P下载</b><br><br>';
    videos.sort(sortBw);
    videos.forEach((video) => {
      var { width, height, baseUrl: videoUrl, bandwidth: videoBw } = video;
      var url = audioUrl + '|' + videoUrl;
      var timelength = Math.floor(duration / 60);
      html += `${ width + 'x' + height + pad + timelength + '分钟' + pad }<a href="${url}">右键复制链接地址</a><br/><br/>`;
    });
    
    html += '<b>多P下载</b><br><br>';
    html += `<a href="${window.location.href}">右键复制链接地址</a><br><br>`;
    openDialog(`视频链接 m4s (playinfo source: ${playinfoSource})`, html);
  } else if (data.durl) {
    var tasks = [];
    
    if (playinfoUrl) {
      tasks = data.accept_quality.map(each => new Promise(resolve => {
        var url = playinfoUrl.replace(/qn=\d+/, 'qn=' + each);
        fetch(url, {credentials: 'include'}).then(resp => resp.json()).then(rs => {
          resolve(rs.result || rs.data)
        })
      }));
    } else {
      tasks = [Promise.resolve(data)];
    }
    
    Promise.all(tasks).then(playinfoList => {
      var html = '<b>单P下载</b><br><br>';
      playinfoList.forEach(each => {
        var { timelength, format, durl } = each;
        var size = 0, urls = [];
        for (var each of durl) {
          size += each.size;
          urls.push(each.url);
        }
        var url = urls.join('|');
        size = Math.floor(size / 1024 / 1024);
        timelength = Math.floor(timelength / 1000 / 60);

        html += `${format + pad + timelength + '分钟' + pad + size + 'MB' + pad + '分' + urls.length + '段' + pad}<a href="${url}">右键复制链接地址</a><br><br>`;
      });
      
      html += '<b>多P下载</b><br><br>';
      if (playinfoUrl) {
        var pageUrl = window.location.href;
        pageUrl = pageUrl.indexOf('?') != -1 ? pageUrl : pageUrl + '?';
        var playinfoBaseUrl = playinfoUrl.replace(/&cid=[^&]+?$|cid=.+?&/, '');
        var sessCookie = document.cookie.split('; ').filter(each => each.startsWith('SESSDATA='));
        sessCookie = sessCookie.length ? sessCookie[0] : '';

        var url = `${pageUrl}|${playinfoBaseUrl}|${sessCookie}`;
        var tips = sessCookie ? '' : '未登录或cookie中的SESSDATA项的HttpOnly属性为true，只能获取低清晰度版本';

        html += `${tips + pad}<a href="${url}">右键复制链接地址</a><br><br>`;
      } else {
        html += `<a href="${window.location.href}">右键复制链接地址</a><br><br>`;
      }
      
      openDialog(`视频链接 flv (playinfo source: ${playinfoSource})`, html); 
    });
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
  playinfoSource = "";
  playinfoUrl = "";
  return window.history._pushState(...arguments);
}
window.history.replaceState = function() {
  handled = false;
  playinfoSource = "";
  playinfoUrl = "";
  return window.history._replaceState(...arguments);
}
