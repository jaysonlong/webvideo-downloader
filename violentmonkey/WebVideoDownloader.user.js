// ==UserScript==
// @name 网站视频下载器
// @namespace https://github.com/jaysonlong
// @author Jayson Long https://github.com/jaysonlong
// @version 1.4
// @match *://www.bilibili.com/*/play/*
// @match *://www.bilibili.com/video/*
// @match *://www.iqiyi.com/*.html*
// @match *://v.qq.com/x/cover/*
// @match *://v.qq.com/x/page/*
// @match *://www.mgtv.com/b/*
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @require https://cdn.bootcdn.net/ajax/libs/draggabilly/2.3.0/draggabilly.pkgd.min.js
// @require https://cdn.bootcdn.net/ajax/libs/limonte-sweetalert2/8.11.8/sweetalert2.all.min.js
// @run-at document-start
// @grant GM_xmlhttpRequest
// @inject-into page
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/WebVideoDownloader.user.js
// @homepageURL https://github.com/jaysonlong/webvideo-downloader
// ==/UserScript==


var storage = {
  // 通用
  serverAddr: '127.0.0.1:18888',
  cbFn: {},
  downloadBtn: null,
  downloadModal: null,
  playinfoUrl: null,

  // bilibili
  playinfoSource: null,

  // 腾讯视频
  playinfoMethod: null,
  playinfoBody: null,
};

var domains = ['bilibili.com', 'iqiyi.com', 'qq.com', 'mgtv.com'];

var handler = {
  'bilibili.com': function() {
    // 首次加载
    $.ready(function() {
      var ele = $('script', each => each.innerText.includes('__playinfo__'));
      if (ele.length) {
        storage.playinfoSource = "embedded html";
        eval(ele[0].innerText);
        bilibili_parseResult(window.__playinfo__);
      }
    });
    // 单页跳转
    ajaxHook({
      open: function([_, url], xhr) {
        if (url.indexOf('playurl?') > 0) {
          storage.playinfoSource = "xhr request";
          storage.playinfoUrl = url.startsWith('http') ? url : location.protocol + url;
          fetch(storage.playinfoUrl, {
            credentials: 'include'
          }).then(resp => resp.json()).then(bilibili_parseResult);
        }
      }
    });
  },

  'iqiyi.com': function() {
    ajaxHook({
      open: function([_, url]) {
        if (url.indexOf('dash?') > 0) {
          storage.playinfoUrl = url;
          fetch(url, {
            credentials: 'include'
          }).then(resp => resp.json()).then(iqiyi_parseResult);
        }
      }
    });
  },

  'qq.com': function() {
    ajaxHook({
      open: ([method, url], xhr) => {
        xhr.method = method;
        xhr.url = url;
      },
      send: ([body], xhr) => {
        if (xhr.url.indexOf('qq.com/proxyhttp') > 0 && body.indexOf('vinfoparam') > 0) {
          xhr.body = body;
        }
      },
      onreadystatechange: function(xhr) {
        if (xhr.body && xhr.readyState == 4) {
          Object.assign(storage, {
            playinfoUrl: xhr.url,
            playinfoMethod: xhr.method,
            playinfoBody: xhr.body,
          });
          tencent_parseResult(xhr.responseText);
        }
      },
    });
  },

  'mgtv.com': function() {
    jsonpHook('getSource?', mgtv_parseResult);
  },
}

prepare();
domains.some(domain => {
  if (location.href.indexOf(domain) != -1) {
    handler[domain]();
    return true;
  }
});


// --------------------------------------------------------------

// bilibili: 获取视频链接
async function bilibili_parseResult(rs) {
  var data = rs.result || rs.data;
  $.logEmphasize('VideoInfo', data);

  var htmls = [];
  htmls.push(`<b>单P下载 (${storage.playinfoSource})</b>`);
  var singlePartHtmls = await bilibili_singlePart(data);
  htmls = htmls.concat(singlePartHtmls)

  htmls.push('<b>多P下载</b>');
  if (storage.playinfoUrl) {
    var pageUrl = location.href;
    pageUrl = pageUrl.indexOf('?') != -1 ? pageUrl : pageUrl + '?';
    var playinfoBaseUrl = storage.playinfoUrl.replace(/&cid=[^&]+?$|cid=.+?&/, '');
    var sessCookie = document.cookie.split('; ').filter(each => each.startsWith('SESSDATA='));
    sessCookie = sessCookie.length ? sessCookie[0] : '';

    var url = `${pageUrl}|${playinfoBaseUrl}|${sessCookie}`;
    var tips = sessCookie ? '' : '未登录或cookie中的SESSDATA项的HttpOnly属性为true，只能获取低清晰度版本';
    htmls.push(`${tips}  ${createLink(url, 'remote multi')}`);
  } else {
    htmls.push(createLink(location.href, 'remote multi'));
  }

  $.waitForTitleChange(() => updateModal({
    title: document.title,
    content: htmls.join('\n'),
  }), storage.downloadBtn ? 3000 : 0);
}

// bilibili: 获取单P视频链接
async function bilibili_singlePart(data) {
  var htmls = [];

  if (data.dash) {
    var sortBw = function(a, b) {
      return b.id != a.id ? b.id - a.id : b.bandwidth - a.bandwidth;
    }
    var { baseUrl: audioUrl } = data.dash.audio.sort(sortBw)[0];
    var defns = [];
    data.dash.video.sort(sortBw).forEach(video => {
      if (defns.includes(video.id)) return;
      defns.push(video.id);

      var { width, height, baseUrl: videoUrl } = video;
      var url = audioUrl + '|' + videoUrl;
      var timelength = Math.floor(data.dash.duration / 60);
      var fileformat = url.match(/[^/?]+\.([^/?]+)\?/)[1];
      var html = `${width}x${height}  ${fileformat}  ${timelength}分钟  ${createLink(url)}`;
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
      var { timelength, durl, format: fileformat } = playinfo;
      var size = 0, urls = [], url;
      for (var each of durl) {
        size += each.size;
        urls.push(each.url);
      }
      url = urls.join('|');
      size = Math.floor(size / 1024 / 1024);
      timelength = Math.floor(timelength / 1000 / 60);
      return `${fileformat}  ${timelength}分钟  ${size}MB  分${urls.length}段  ${createLink(url)}`;
    });
  }
  return htmls;
}


// 爱奇艺: 获取视频链接
function iqiyi_parseResult(rs) {
  $.logEmphasize('VideoInfo', rs);

  var videos = rs.data.program.video.filter(each => each.m3u8 != undefined);
  if (videos.length) {
    var {
      vid,
      m3u8,
      vsize: size,
      ff: fileformat,
      scrsz: wh,
    } = videos[0];
    var size = Math.floor(size / 1024 / 1024);
    var html = `${fileformat}  ${wh}  ${size}M  ${createLink(storage.playinfoUrl)}`;

    $.waitForTitleChange(() => updateModal({
      title: document.title,
      content: html,
    }), storage.downloadBtn ? 3000 : 0);
  }
};


// 腾讯视频: 获取视频链接
function tencent_parseResult(rs) {
  var data = typeof rs == "string" ? JSON.parse(rs) : rs;
  var vinfo = JSON.parse(data.vinfo);

  $.logEmphasize('VideoInfo', vinfo);

  var tasks = vinfo.fl.fi.map(each => new Promise(resolve => {
    var { name: defn, cname: defDesc } = each;
    var body = storage.playinfoBody.replace(/defn=[^&]*/, 'defn=' + defn);
    fetch(storage.playinfoUrl, {
        body: body,
        method: storage.playinfoMethod,
      })
      .then(resp => resp.json())
      .then(data => ({ defDesc, data }))
      .then(resolve);
  }));

  Promise.all(tasks).then(rsList => {
    var html = '';
    rsList.forEach(each => {
      try {
        var { url, width, height, size } = tencent_parseVideoInfo(each.data);
        html += `${width}x${height}  ${each.defDesc}  ${size}M  ${createLink(url)}\n`;
      } catch (e) {}
    })

    updateModal({
      title: document.title,
      content: html,
    });
  });
}

// 腾讯视频: 解析视频信息
function tencent_parseVideoInfo(data) {
  var vinfo = JSON.parse(data.vinfo);
  var vi = vinfo.vl.vi[0];
  var ui = vi.ul.ui[0];
  var url = ui.url;
  if (url.indexOf('.m3u8') == -1) {
    url += ui.hls.pt;
  }
  var { vw: width, vh: height, fs: size } = vi;
  size = Math.floor(size / 1024 / 1024);
  return { url, width, height, size }
}

// 芒果TV: 获取视频链接
function mgtv_parseResult(rs) {
  $.logEmphasize('VideoInfo', rs);

  var host = rs.data.stream_domain[0];
  var videoInfo = rs.data.stream.filter(each => each.url != '');
  var tasks = videoInfo.map((each, i) => new Promise(resolve => {
    var { fileformat, name, url } = each;
    url = host + each.url;
    
    $.jsonp(url).then(rs => {
      var url = rs.info;
      fetch(url).then(resp => resp.text()).then(rs => {
        var { width, height, size } = mgtv_parseVideoInfo(rs);
        resolve({ width, height, size, fileformat, name, url });
      });
    });
  }));

  Promise.all(tasks).then(rsList => {
    var html = '';
    rsList.forEach(rs => {
      var { width, height, size, fileformat, name, url } = rs;
      html += `${width}x${height}  ${fileformat}  ${name}  ${size}M  ${createLink(url)}\n`;
    })

    updateModal({
      title: document.title,
      content: html,
    });
  })
}

// 芒果TV: 解析视频信息
function mgtv_parseVideoInfo(rs) {
  var width = rs.match(/EXT-MGTV-VIDEO-WIDTH:(\d+)/)[1];
  var height = rs.match(/EXT-MGTV-VIDEO-HEIGHT:(\d+)/)[1];
  var size = 0;
  rs.match(/#EXT-MGTV-File-SIZE:\d+/g).forEach(each => {
    var eachSize = parseInt(each.split(':')[1]);
    size += eachSize;
  });
  size = Math.floor(size / 1024 / 1024);
  return { width, height, size }
}

// 调用下载器创建任务
async function remoteCall(url, multi) {
  var queue = [{title:'输入文件名', inputValue: storage.downloadModal.title}];
  multi && queue.push('输入首、尾P(空格分隔)或单P');
  Swal.mixin({
    input: 'text',
    showCancelButton: true,
    confirmButtonText: '<i class="fa fa-arrow-right"></i>',
    cancelButtonText: '<i class="fa fa-times"></i>',
    progressSteps: Object.keys(queue).map(idx => parseInt(idx) + 1),
  }).queue(queue).then((result) => {
    if (result.value) {
      var payload = {
        fileName: result.value[0],
        pRange: result.value[1],
        linksurl: url,
        type: 'link',
      }
      httpCall(payload).then(msg => {
        Swal.fire({
          type: 'success',
          title: msg,
          position: 'top-end',
          showConfirmButton: false,
          timer: 1000
        });
      }).catch(msg => {
        Swal.fire({
          type: 'error',
          title: msg,
        });
      });
    }
  })
}

// http调用，不受CSP限制
function httpCall(payload) {
  return new Promise((resolve, reject) => {
    GM_xmlhttpRequest({
      method: "POST",
      url: 'http://' + storage.serverAddr,
      data: JSON.stringify(payload),
      timeout: 600,
      onload: function(res) {
        if (res.response == 'success') {
          resolve('任务已创建');
        } else {
          reject('创建任务失败');
        }
      },
      ontimeout: function() {
        reject('请先运行 "python daemon.py"');
      }
    });
  });
}

// websocket调用，CSP限制只能使用本地服务器，支持MSE流
function wsCall(payload) {
  return new Promise((resolve, reject) => {
    var ws = new WebSocket('ws://' + storage.serverAddr);
    ws.onerror = function() {
      reject('请先运行 "python daemon.py"');
    };
    ws.onopen = function() {
      ws.send(JSON.stringify(payload));
      ws.onmessage = e => {
        if (e.data == 'success') {
          resolve('任务已创建');
        } else {
          resolve('创建任务失败');
        }
        ws.close();
      }
    };
  });
}

// 更新下载内容（设置模态框的标题和正文）
function updateModal({title, content}) {
  storage.downloadModal = {title, content};
  if (storage.downloadBtn) return;

  storage.downloadBtn = $.create('div', {
    id: 'dl-btn', 
    innerHTML: '<span>下载<br>视频</span>',
    appendToBody: true,
  });
  var draggie = new Draggabilly(storage.downloadBtn);
  draggie.on('staticClick', e => {
    Swal.fire({
      title: storage.downloadModal.title,
      html: storage.downloadModal.content,
      customClass: {
        container: 'dl-modal',
        title: 'dl-modal-title',
        content: 'dl-modal-content',
      },
      showCloseButton: true,
      showConfirmButton: false,
      focusConfirm: false,
    });
    $('.dl-modal')[0].on('click', '.remote', e => {
      e.preventDefault();
      remoteCall(e.target.href, e.target.classList.contains('multi'));
    });
  });
}

function createLink(url, clz = 'remote', text = '点击下载或复制链接') {
  return `<a href="${url}" class="${clz}">${text}</a>`;
}


// --------------------------------------------------------------


// ajax拦截
function ajaxHook() {
  ah.hook(...arguments);
  unsafeWindow.XMLHttpRequest = XMLHttpRequest;
}

// jsonp拦截
function jsonpHook(urlKey, cbFunc, cbKey = 'callback') {
  document._createElement = document.createElement;
  document.createElement = function(type) {
    var ele = document._createElement(type);
    if (type.toLowerCase() == 'script') {
      setTimeout(() => {
        if (ele.src.indexOf(urlKey) > 0) {
          var cbName = ele.src.match(new RegExp(cbKey + '=([^&]+)'))[1];
          if (!storage.cbFn[cbName]) {
            storage.cbFn[cbName] = unsafeWindow[cbName];
            Object.defineProperty(unsafeWindow, cbName, {
              get: () => {
                if (!storage.cbFn[cbName]) {
                  return undefined;
                }
                return (rs) => {
                  try {
                    cbFunc(rs);
                  } catch (e) {}
                  storage.cbFn[cbName](rs);
                };
              },
              set: (fn) => {
                storage.cbFn[cbName] = fn;
              }
            });
          }
        }

      }, 0);
    }
    return ele;
  }
}

// 元素选择器
function $(selector, filterFn = null) {
  var eles = Array(...document.querySelectorAll(selector));
  return filterFn ? eles.filter(filterFn) : eles;
}

// 初始化工作
function prepare() {
  Object.assign($, {
    create: function(tagName, attrs = {}) {
      var ele = document.createElement(tagName);
      Object.assign(ele, attrs);
      if (attrs.appendToBody) {
        document.body.appendChild(ele);
      }
      return ele;
    },
    ready: function(callback) {
      document.addEventListener("DOMContentLoaded", callback);
    },
    addStyle: function(source) {
      if (source.startsWith('http')) {
        $.create('link', {
          rel: 'stylesheet',
          href: source,
          appendToBody: true,
        })
      } else {
        $.create('style', {
          innerText: source,
          appendToBody: true,
        })
      }
    },
    jsonp: function(url, cbKey = 'callback') {
      $.counter = $.counter ? $.counter + 1 : 1;
      var cbName = 'jaysonCb' + $.counter;

      return new Promise(resolve => {
        var script = $.create('script', {
          src: `${url}&${cbKey}=${cbName}`,
          appendToBody: true,
        });
        unsafeWindow[cbName] = function(data) {
          resolve(data);
          script.remove();
          unsafeWindow[cbName] = undefined;
        };
      })
    },
    waitForTitleChange: function(callback, timeout = 0) {
      var handled = false;
      var wrappedCb = () => handled || (handled = true) && callback();
      $('title')[0].on('childListChanged', wrappedCb, true);
      setTimeout(wrappedCb, timeout);
    },
    logEmphasize: function() {
      var args = [...arguments];
      args.splice(0, 1, '%c' + args[0], 'color:green;font-size:1.3em;font-weight:bold;background:#abfdc1;');
      console.log(...args);
    }
  });

  Object.assign(HTMLElement.prototype, {
    is: function(selector) {
      return $(selector).includes(this);
    },
    on: function(event, arg1, arg2) {
      if (event === 'childListChanged') {
        var [listener, once] = [arg1, arg2];
        var observer = new MutationObserver(function() {
            listener.call(this);
            once && observer.disconnect();
        });
        observer.observe(this, {childList: true});
      } else {
        var [selector, listener] = arg2 instanceof Function ? [arg1, arg2] : [null, arg1];
        this.addEventListener(event, e => {
          if (!selector || e.target.is(selector)) {
            listener.call(e.target, e);
          }
        });
      }
      return this;
    },
  });

  $.ready(() => {
    $.addStyle('https://cdn.bootcdn.net/ajax/libs/font-awesome/4.0.0/css/font-awesome.min.css');
    $.addStyle(`
      #dl-btn {
        z-index: 1000;
        position: fixed;
        top: 200px;
        left: 5px;
        width: 50px;
        height: 50px;
        line-height: 50px;
        border-radius: 50%;
        border: #fff solid 1.5px;
        box-shadow: 0 3px 10px rgb(48, 133, 214);
        text-align: center;
        background: rgb(48, 133, 214);
        color: white;
        cursor: pointer;
      }
      #dl-btn:hover {
        background-image: linear-gradient(rgba(0,0,0,.1),rgba(0,0,0,.1));
      }
      #dl-btn span {
        display: inline-block;
        font-size: 12px;
        line-height: 15px;
        vertical-align: middle;
      }
      .dl-modal-title {
        font-size: 18px;
      }
      .dl-modal-content {
        font-size: 15px;
        line-height: 30px;
        white-space: pre;
      }
      .dl-modal-content a {
        color: blue;
      }
      .dl-modal-content b {
        font-weight: bold;
      }
    `);
  });
}
