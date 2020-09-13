// ==UserScript==
// @name 通用hls下载器
// @namespace https://github.com/jaysonlong
// @author Jayson Long https://github.com/jaysonlong
// @version 1.2.1
// @require https://unpkg.com/ajax-hook@2.0.0/dist/ajaxhook.min.js
// @require https://cdn.bootcdn.net/ajax/libs/draggabilly/2.3.0/draggabilly.pkgd.min.js
// @require https://cdn.bootcdn.net/ajax/libs/limonte-sweetalert2/8.11.8/sweetalert2.all.min.js
// @run-at document-start
// @grant GM_xmlhttpRequest
// @inject-into page
// @downloadURL https://github.com/jaysonlong/webvideo-downloader/raw/master/violentmonkey/CommonHlsDownloader.user.js
// @homepageURL https://github.com/jaysonlong/webvideo-downloader
// ==/UserScript==


var storage = {
  serverAddr: '127.0.0.1:18888',
  downloadBtn: null,
  modalInfo: null,
};

prepare();

setTimeout(() => {
  if (unsafeWindow.webvideo_downloader_exist) return;
  // ajax拦截
  ajaxHook({
    open: function([method, url], xhr) {
      if (url.indexOf('.m3u8') > -1) {
        $.logEmphasize('m3u8Url', url);
        var html = `<a href="${url}" class="remote">点击下载或复制链接</a>`;

        updateModal({
          title: document.title,
          content: html,
        });
      }
    },
  });
});


// 更新下载内容（设置模态框的标题和正文）
function updateModal({title, content}) {
  storage.modalInfo = {title, content};
  if (storage.downloadBtn) return;

  storage.downloadBtn = $.create('div', {
    id: 'dl-btn', 
    innerHTML: '<span>下载<br>视频</span>',
    appendToBody: true,
  });
  var draggie = new Draggabilly(storage.downloadBtn);
  draggie.on('staticClick', e => {
    Swal.fire({
      title: storage.modalInfo.title,
      html: storage.modalInfo.content,
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
      prepareDownload(e.target.href);
    });
  });
}

// 准备下载信息
function prepareDownload(url) {
  Swal.fire({
    input: 'text',
    showCancelButton: true,
    confirmButtonText: '<i class="fa fa-arrow-right"></i>',
    cancelButtonText: '<i class="fa fa-times"></i>',
    title: '输入文件名',
    inputValue: storage.modalInfo.title,
  }).then((result) => {
    if (result.value) {
      var payload = {
        fileName: result.value,
        linksurl: url,
        type: 'link',
      }

      // 创建下载任务
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

// http调用，不受CSP和Mixed Content限制
function httpCall(payload) {
  return new Promise((resolve, reject) => {
    GM_xmlhttpRequest({
      method: "POST",
      url: 'http://' + storage.serverAddr,
      data: JSON.stringify(payload),
      timeout: 1000,
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

// ajax拦截
function ajaxHook() {
  ah.hook(...arguments);
  unsafeWindow.XMLHttpRequest = XMLHttpRequest;
}

// 元素选择器
function $(selector, filterFn = null) {
  var eles = Array(...document.querySelectorAll(selector));
  return filterFn ? eles.filter(filterFn) : eles;
}

// 初始化工作
function prepare() {
  console._log = console.log;
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
    logEmphasize: function() {
      var args = [...arguments];
      args.splice(0, 1, '%c' + args[0], 'color:green;font-size:1.3em;font-weight:bold;background:#abfdc1;');
      console._log(...args);
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
    $.create('i', { 
      className: 'fa fa-arrow-right fa-times', 
      style: 'visibility:hidden;height:0;width:0;', 
      appendToBody: true,
    });
    $.addStyle('https://cdn.bootcdn.net/ajax/libs/font-awesome/4.0.0/css/font-awesome.min.css');
    $.addStyle(`
      .swal2-container {
        font-size: 18px;
      }
      .swal2-modal {
        font-size: 1em;
      }
      #dl-btn {
        z-index: 1000;
        position: fixed;
        top: 200px;
        left: 5px;
        width: 50px;
        height: 50px;
        line-height: 50px;
        font-size: 12px;
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
        white-space: pre-wrap;
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
