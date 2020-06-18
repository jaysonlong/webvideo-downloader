// ==UserScript==
// @name 网站视频下载器
// @namespace https://github.com/jaysonlong
// @author Jayson Long https://github.com/jaysonlong
// @version 1.2
// @match *://www.bilibili.com/*/play/*
// @match *://www.bilibili.com/video/*
// @match *://www.iqiyi.com/*.html
// @match *://v.qq.com/x/cover/*
// @match *://v.qq.com/x/page/*
// @match *://www.mgtv.com/b/*
// @require https://cdn.bootcdn.net/ajax/libs/jquery/1.7.2/jquery.min.js
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @run-at document-start
// @grant none
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js
// @homepageURL https://github.com/jaysonlong/webvideo-downloader
// ==/UserScript==

var pad = '&nbsp;&nbsp;';
var serverUrl = 'ws://localhost:18888';
var cbFn = {};
var handled = false;

var storage = {
  // bilibili
  playinfoSource: 0,
  playinfoUrl: 0,

  // 腾讯视频
  url: 0,
  method: 0,
  body: 0,
};

var isIqiyi = location.href.indexOf('iqiyi.com') > 0;
var isBilibili = location.href.indexOf('bilibili.com') > 0;
var isTencent = location.href.indexOf('qq.com') > 0;
var isMGTV = location.href.indexOf('mgtv.com') > 0;

if (isBilibili) {
  // 方法1，从html script标签中获取playinfo
  $(() => {
    if (!handled && $('html').html().includes('__playinfo__')) {
      handled = true;
      storage.playinfoSource = "embedded html";

      eval($('script:contains(__playinfo__)').text());
      bilibili_parseResult(window.__playinfo__);
    }
  });

  // 方法2，ajax拦截
  ah.hook({
    open: function(args, xhr) {
      var url = args[1];
      if (!handled && url.indexOf('playurl?') > 0) {
        handled = true;
        storage.playinfoSource = "xhr request";
        storage.playinfoUrl = url.startsWith('http') ? url : window.location.protocol + url;

        fetch(storage.playinfoUrl, {
          credentials: 'include'
        }).then(response => response.json()).then(bilibili_parseResult);
      }
    }
  });

  observeUrl(() => (handled = false));

} else if (isIqiyi) {
  // 方法1，ajax拦截
  ah.hook({
    open: function(args, xhr) {
      var url = args[1];
      if (url.indexOf('dash?') > 0) {
        iqiyi_parseUrl(url);
      }
    }
  });

  // 方法2，jsonp拦截
  jsonpIntercept('/jp/dash?', iqiyi_parseUrl);

} else if (isTencent) {
  // ajax拦截
  ah.hook({
    open: ([method, url], xhr) => {
      var [method, url] = args;
      xhr.method = method;
      xhr.url = url;
    },
    send: (args, xhr) => {
      var body = args[0];
      if (xhr.url.indexOf('qq.com/proxyhttp') > 0 && body.indexOf('vinfoparam') > 0) {
        xhr.body = body;
      }
    },
    onreadystatechange: function(xhr) {
      if (!handled && xhr.body && xhr.readyState == 4) {
        handled = true;
        Object.assign(storage, {
          url: xhr.url,
          method: xhr.method,
          body: xhr.body,
        });
        tencent_parseResult(xhr.responseText);
      }
    },
  });

  observeUrl(() => (handled = false));

} else if (isMGTV) {
  // jsonp拦截
  jsonpIntercept('getSource?', mgtv_parseResult);
}


// bilibili: 获取视频链接
async function bilibili_parseResult(rs) {
  var data = rs.result || rs.data;
  console.log(data);

  var htmls = [];
  htmls.push('<b>单P下载</b>');
  var singlePartHtmls = await bilibili_fetchHtmls(data);
  htmls = htmls.concat(singlePartHtmls)

  htmls.push('<b>多P下载</b>');
  if (storage.playinfoUrl) {
    var pageUrl = window.location.href;
    pageUrl = pageUrl.indexOf('?') != -1 ? pageUrl : pageUrl + '?';
    var playinfoBaseUrl = storage.playinfoUrl.replace(/&cid=[^&]+?$|cid=.+?&/, '');
    var sessCookie = document.cookie.split('; ').filter(each => each.startsWith('SESSDATA='));
    sessCookie = sessCookie.length ? sessCookie[0] : '';

    var url = `${pageUrl}|${playinfoBaseUrl}|${sessCookie}`;
    var tips = sessCookie ? '' : '未登录或cookie中的SESSDATA项的HttpOnly属性为true，只能获取低清晰度版本';
    htmls.push(tips + pad + toAnchor(url, 'multi'));
  } else {
    htmls.push(toAnchor(location.href, 'multi'));
  }

  htmls = htmls.join('<br><br>')
  openDialog(`视频链接 (playinfo source: ${storage.playinfoSource})`, htmls);
}


async function bilibili_fetchHtmls(data) {
  var htmls = [];

  if (data.dash) {
    var sortBw = function(a, b) {
      return b.id != a.id ? b.id - a.id : b.bandwidth - a.bandwidth;
    }
    var { baseUrl: audioUrl } = data.dash.audio.sort(sortBw)[0];
    var defns = [];
    data.dash.video.sort(sortBw).forEach(video => {
      if (defns.includes(video.id)) {
        return;
      }
      defns.push(video.id);

      var {
        width,
        height,
        baseUrl: videoUrl,
        bandwidth: videoBw
      } = video;
      var url = audioUrl + '|' + videoUrl;
      var timelength = Math.floor(data.dash.duration / 60);
      var fileformat = parseFileExt(url);
      var html = `${width}x${height}` + pad + fileformat + pad + `${timelength}分钟` + pad + toAnchor(url);
      htmls.push(html);
    });
  } else if (data.durl) {
    var tasks;
    if (storage.playinfoUrl) {
      tasks = data.accept_quality.map(each => new Promise(resolve => {
        var url = storage.playinfoUrl.replace(/qn=\d+/, 'qn=' + each);
        fetch(url, { credentials: 'include' }).then(resp => resp.json()).then(rs => {
          resolve(rs.result || rs.data)
        })
      }));
    } else {
      tasks = [Promise.resolve(data)];
    }

    var playinfoList = await tasks;
    htmls = playinfoList.map(playinfo => {
      var {
        timelength,
        format: fileformat,
        durl
      } = playinfo;
      var size = 0, urls = [], url;
      for (var each of durl) {
        size += each.size;
        urls.push(each.url);
      }
      url = urls.join('|');
      size = Math.floor(size / 1024 / 1024);
      timelength = Math.floor(timelength / 1000 / 60);
      return fileformat + pad + `${timelength}分钟` + pad + `${size}MB` + pad + `分${urls.length}段` + pad + toAnchor(url);
    });
  }
  return htmls;
}


// 爱奇艺: 获取m3u8链接
function iqiyi_parseUrl(url) {
  fetch(url, {
    credentials: 'include'
  }).then(response => response.json()).then(rs => {
    console.log(rs);

    var videos = rs.data.program.video.filter(each => each.m3u8 != undefined);
    if (videos.length) {
      var {
        vsize: size,
        m3u8,
        ff: fileformat,
        scrsz: wh,
        vid
      } = videos[0];
      var size = Math.floor(size / 1024 / 1024);
      var downloadAnchor = '';
      // var blob = new Blob([m3u8]);
      // var blobUrl = URL.createObjectURL(blob);
      // downloadAnchor = toAnchor(blobUrl, vid + '.m3u8', '点击下载视频信息');
      var html = `${fileformat + pad + wh + pad + size + 'M' + pad + toAnchor(url) + pad + downloadAnchor}<br><br>`;
      openDialog('视频链接', html);
    }
  });
};


// 腾讯视频: 获取视频链接
function tencent_parseResult(rs) {
  var data = typeof rs == "string" ? JSON.parse(rs) : rs;
  var vinfo = JSON.parse(data.vinfo);

  console.log(vinfo);

  var tasks = vinfo.fl.fi.map(each => new Promise(resolve => {
    var {
      name: defn,
      cname: defdesc
    } = each;
    var body = storage.body.replace(/defn=[^&]*/, 'defn=' + defn);
    fetch(storage.url, {
        body: body,
        method: storage.method,
      })
      .then(resp => resp.json())
      .then(data => ({
        defdesc,
        data
      }))
      .then(resolve);
  }));

  Promise.all(tasks).then(rsList => {
    var html = '';
    rsList.forEach(each => {
      try {
        var {
          url,
          width,
          height,
          size
        } = tencent_parseVideoInfo(each.data);
        html += `${width + 'x' + height + pad + each.defdesc + pad + size + 'M' + pad + toAnchor(url)}<br/><br/>`;
      } catch (e) {}
    })

    openDialog('视频链接', html);
  });
}

// 腾讯视频: 解析视频信息对象
function tencent_parseVideoInfo(data) {
  var vinfo = JSON.parse(data.vinfo);
  var vi = vinfo.vl.vi[0];
  var ui = vi.ul.ui[0];
  var url = ui.url;
  var {
    vw: width,
    vh: height,
    fs: size
  } = vi;
  size = Math.floor(size / 1024 / 1024);

  return {
    url,
    width,
    height,
    size
  }
}

// 芒果TV: 获取视频链接
function mgtv_parseResult(rs) {
  var host = rs.data.stream_domain[0];
  var videoInfo = rs.data.stream.filter(each => each.url != '');
  var tasks = videoInfo.map((each, i) => new Promise(resolve => {
    var {
      fileformat,
      name,
      url
    } = each;
    var ele = document.createElement('script');
    var cb = 'jaysonCb' + i;
    url = host + each.url + '&callback=' + cb;
    ele.src = url;
    document.body.appendChild(ele);

    window[cb] = function(rs) {
      var url = rs.info;
      fetch(url).then(resp => resp.text()).then(rs => {
        var {
          width,
          height,
          size
        } = parseVideoInfo_mgtv(rs);
        resolve({
          width,
          height,
          size,
          fileformat,
          name,
          url
        });
      });

      document.body.removeChild(ele);
      window[cb] = undefined;
    };
  }));

  Promise.all(tasks).then(rsList => {
    var html = '';
    rsList.forEach(rs => {
      var {
        width,
        height,
        size,
        fileformat,
        name,
        url
      } = rs;
      html += `${width + 'x' + height + pad + fileformat + pad + name + pad + size + 'M' + pad + toAnchor(url)}<br><br>`;
    })

    openDialog('视频链接', html);
  })
}

// 芒果TV: 解析视频信息
function parseVideoInfo_mgtv(rs) {
  var width = rs.match(/EXT-MGTV-VIDEO-WIDTH:(\d+)/)[1];
  var height = rs.match(/EXT-MGTV-VIDEO-HEIGHT:(\d+)/)[1];
  var size = 0;
  rs.match(/#EXT-MGTV-File-SIZE:\d+/g).forEach(each => {
    var eachSize = parseInt(each.split(':')[1]);
    size += eachSize;
  });
  size = Math.floor(size / 1024 / 1024);

  return {
    width,
    height,
    size
  }
}

// jsonp拦截
function jsonpIntercept(urlKey, cbFunc, cbKey = 'callback') {
  document._createElement = document.createElement;
  document.createElement = function(type) {
    var ele = document._createElement(type);

    if (type.toLowerCase() == 'script') {
      setTimeout(() => {
        if (ele.src.indexOf(urlKey) > 0) {
          var cbName = ele.src.match(new RegExp(cbKey + '=([^&]+)'))[1];

          if (!cbFn[cbName]) {
            cbFn[cbName] = window[cbName];
            Object.defineProperty(window, cbName, {
              get: () => {
                if (!cbFn[cbName]) {
                  return undefined;
                }
                return (rs) => {
                  try {
                    cbFunc(rs);
                  } catch (e) {}
                  cbFn[cbName](rs);
                };
              },
              set: (fn) => {
                cbFn[cbName] = fn;
              }
            });
          }
        }
      }, 0);
    }

    return ele;
  }
}

// 检测url变化
function observeUrl(cbFunc) {
  window.history._pushState = window.history.pushState;
  window.history._replaceState = window.history.replaceState;

  window.history.pushState = function() {
    cbFunc();
    return window.history._pushState(...arguments);
  }
  window.history.replaceState = function() {
    cbFunc();
    return window.history._replaceState(...arguments);
  }
}

function parseFileExt(url) {
  return url.match(/[^/?]+\.([^/?]+)\?/)[1];
}

function toAnchor(url, type = 'single', text = '点击下载或复制链接') {
  if (type == 'single') {
    return `<a class="remote" href="${url}">${text}</a>`;
  } else if (type == 'multi') {
    return `<a data-multi="multi" class="remote" href="${url}">${text}</a>`;
  } else {
    return `<a download="${type}" href="${url}">${text}</a>`;
  }
}

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