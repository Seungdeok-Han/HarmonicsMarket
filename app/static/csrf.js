/** Attach CSRF token to same-origin fetch/XHR POST/PUT/PATCH/DELETE requests. */
(function () {
  function token() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  var originalFetch = window.fetch;
  if (originalFetch) {
    window.fetch = function (input, init) {
      init = init || {};
      var method = (init.method || 'GET').toUpperCase();
      if (['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1) {
        var headers = new Headers(init.headers || {});
        if (!headers.has('X-CSRFToken') && !headers.has('X-CSRF-Token')) {
          headers.set('X-CSRFToken', token());
        }
        init.headers = headers;
      }
      return originalFetch.call(this, input, init);
    };
  }
})();
