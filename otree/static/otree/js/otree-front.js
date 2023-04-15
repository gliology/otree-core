/*!
otree-front v1.2.0
microframework for interactive pages for oTree platform
(C) qwiglydee@gmail.com
https://github.com/qwiglydee/otree-front
*/
var ot = (function (exports) {
    'use strict';

    function isArray(o) {
      return Array.isArray(o);
    }
    function isFunction(obj) {
      return typeof obj == "function";
    }
    function isVoid(value) {
      return value === undefined || value === null || Number.isNaN(value);
    }
    function isHTMLElement(value) {
      return Object.prototype.toString.call(value).startsWith("[object HTML");
    }

    /**
     * from https://github.com/oleics/node-is-scalar
     */
    function isScalar(value) {
      var type = typeof value;
      if (type === 'string') return true;
      if (type === 'number') return true;
      if (type === 'boolean') return true;
      if (type === 'symbol') return true;
      if (value == null) return true;
      if (value instanceof Symbol) return true;
      if (value instanceof String) return true;
      if (value instanceof Number) return true;
      if (value instanceof Boolean) return true;
      return false;
    }

    /*
     * is-plain-object <https://github.com/jonschlinkert/is-plain-object>
     *
     * Copyright (c) 2014-2017, Jon Schlinkert.
     * Released under the MIT License.
     */

    function isObject(o) {
      return Object.prototype.toString.call(o) === '[object Object]';
    }
    function isPlainObject(o) {
      var ctor, prot;
      if (isObject(o) === false) return false;

      // If has modified constructor
      ctor = o.constructor;
      if (ctor === undefined) return true;

      // If has modified prototype
      prot = ctor.prototype;
      if (isObject(prot) === false) return false;

      // If constructor does not have an Object-specific method
      if (prot.hasOwnProperty('isPrototypeOf') === false) {
        return false;
      }

      // Most likely a plain Object
      return true;
    }
    function matchType(value, type) {
      switch (type) {
        case 'data':
          return true;
        case 'array':
          return isArray(value);
        case 'object':
          return isObject(value);
        default:
          return typeof value === type;
      }
    }
    function matchTypes(args, types) {
      return Array.from(args).every((a, i) => matchType(a, types[i]));
    }
    function assertArgs(fname, args) {
      for (var _len = arguments.length, types = new Array(_len > 2 ? _len - 2 : 0), _key = 2; _key < _len; _key++) {
        types[_key - 2] = arguments[_key];
      }
      let matching = types.filter(argtypes => argtypes.length == args.length && matchTypes(args, argtypes));
      if (matching.length == 0) {
        const usage = types.map(argtypes => "".concat(fname, "(").concat(argtypes.join(", "), ")")).join(" or ");
        throw new Error("Invalid arguments, expected: ".concat(usage));
      }
    }

    function emitEvent(name, data) {
      assertArgs("emitEvent", arguments, ['string', 'data'], ['string']);
      let event = new CustomEvent("ot.".concat(name), {
        detail: data
      });
      // NB: queueing via timeout to run like a normal event asynchronousely
      setTimeout(() => document.body.dispatchEvent(event));
    }

    function _defineProperty(obj, key, value) {
      key = _toPropertyKey(key);
      if (key in obj) {
        Object.defineProperty(obj, key, {
          value: value,
          enumerable: true,
          configurable: true,
          writable: true
        });
      } else {
        obj[key] = value;
      }
      return obj;
    }
    function _toPrimitive(input, hint) {
      if (typeof input !== "object" || input === null) return input;
      var prim = input[Symbol.toPrimitive];
      if (prim !== undefined) {
        var res = prim.call(input, hint || "default");
        if (typeof res !== "object") return res;
        throw new TypeError("@@toPrimitive must return a primitive value.");
      }
      return (hint === "string" ? String : Number)(input);
    }
    function _toPropertyKey(arg) {
      var key = _toPrimitive(arg, "string");
      return typeof key === "symbol" ? key : String(key);
    }

    /**
     * Utils to work with dot-separated key paths
     */

    const PATH_RE = /^[a-zA-Z]\w+(\.\w+)*$/;
    function validate(path) {
      return path.match(PATH_RE);
    }
    function length(path) {
      return path.split('.').length;
    }
    function includes(path, nested) {
      return nested == path || nested.startsWith(path + ".");
    }
    function affects(path, watch) {
      return includes(path, watch) || watch.endsWith(".*") && path.startsWith(watch.slice(0, -2));
    }
    function extract(obj, path) {
      if (path.endsWith(".*")) path = path.slice(0, -2);
      return path.split(".").reduce((o, k) => o && k in o ? o[k] : undefined, obj);
    }
    function update(obj, path, value) {
      const keys = path.split(".");
      const parent_path = keys.slice(0, -1);
      const fld = keys.slice(-1)[0];
      function extract(obj, path) {
        return path.reduce((o, k) => o && k in o ? o[k] : undefined, obj);
      }
      let parent = parent_path.length ? extract(obj, parent_path) : obj;
      if (parent === undefined) throw new Error("Unreachable keypath ".concat(path));
      parent[fld] = value;
    }
    function upsert(obj, path, value) {
      const keys = path.split(".");
      const parent_path = keys.slice(0, -1);
      const fld = keys.slice(-1)[0];
      function extract(obj, path) {
        return path.reduce((o, k) => o && k in o ? o[k] : undefined, obj);
      }
      let parent = parent_path.length ? extract(obj, parent_path) : obj;
      if (parent === undefined) throw new Error("Unreachable keypath ".concat(path));
      parent[fld] = value;
    }

    var keypath = /*#__PURE__*/Object.freeze({
        __proto__: null,
        affects: affects,
        extract: extract,
        includes: includes,
        length: length,
        update: update,
        upsert: upsert,
        validate: validate
    });

    function affecting(changes, path) {
      return Array.from(changes.keys()).some(key => affects(key, path));
    }
    const VARPATH = '([a-zA-Z]\\w+(\\.\\w+)*)';
    class Expr {
      static match(expr) {
        if (expr.match(this.banned)) throw new Error("banned expression");
        let match = expr.match(this.regexp);
        if (!match) throw new Error("invalid expression");
        return match;
      }
      affected(changes) {
        return false;
      }
      eval(context) {
        return undefined;
      }
      value(context) {
        return undefined;
      }
    }

    /** just a name expression for ot-emit or onEvent */
    _defineProperty(Expr, "regexp", new RegExp("^" + VARPATH + "$"));
    _defineProperty(Expr, "banned", new RegExp("^(true|false|null|undefined)$"));
    class NameExpr extends Expr {
      constructor(expr) {
        super();
        let match = this.constructor.match(expr);
        this.name = match[1];
      }
    }
    _defineProperty(NameExpr, "description", "name");
    _defineProperty(NameExpr, "regexp", new RegExp("^([a-zA-Z][a-zA-Z0-9\._-]+)$"));
    _defineProperty(NameExpr, "banned", new RegExp("^(true|false|null|undefined)$"));
    class ConstExpr extends Expr {
      constructor(expr) {
        super();
        this.val = JSON.parse(expr.replaceAll("'", '"'));
      }
      eval(data) {
        return this.val;
      }
      value(data) {
        return this.val;
      }
    }

    /** an expression referencing var or obj field */
    _defineProperty(ConstExpr, "description", "value");
    class VarExpr extends Expr {
      constructor(expr) {
        super();
        let match = this.constructor.match(expr);
        this.var = match[1];
      }
      affected(changes) {
        return affecting(changes, this.var);
      }
      eval(data) {
        return extract(data, this.var);
      }
      value(data) {
        return extract(data, this.var);
      }
    }
    _defineProperty(VarExpr, "description", "variable");
    class ObjExpr extends Expr {
      constructor(expr) {
        super();
        let match = this.constructor.match(expr);
        this.var = match[1];
      }
      affected(changes) {
        return affecting(changes, this.var + ".*");
      }
      eval(data) {
        return extract(data, this.var);
      }
      value(data) {
        return extract(data, this.var);
      }
    }

    /** comparision expression */
    _defineProperty(ObjExpr, "description", "object");
    _defineProperty(ObjExpr, "regexp", new RegExp("^" + VARPATH + "\\.\\*$"));
    class CmpExpr extends Expr {
      constructor(expr) {
        super();
        let match = this.constructor.match(expr);
        this.var = match[1];
        this.cmp = match[3];
        this.val = JSON.parse(match[4].replaceAll("'", '"'));
        if (this.val === true || this.val === false || this.val === null) {
          this.cmp += "=";
        }
      }
      affected(changes) {
        return affecting(changes, this.var);
      }
      eval(data) {
        let val = this.value(data);
        if (val === undefined || val === null || Number.isNaN(val)) return false;
        switch (this.cmp) {
          case "==":
            return val == this.val;
          case "!=":
            return val != this.val;
          case "===":
            return val === this.val;
          case "!==":
            return val !== this.val;
        }
      }
      value(data) {
        return extract(data, this.var);
      }
    }

    /** assignment expresion for inputs */
    _defineProperty(CmpExpr, "description", "comparision");
    _defineProperty(CmpExpr, "regexp", new RegExp("^" + VARPATH + " (==|!=) (.+)$"));
    class AssignExpr extends Expr {
      constructor(expr) {
        super();
        let match = this.constructor.match(expr);
        this.var = match[1];
        this.val = JSON.parse(match[3].replaceAll("'", '"'));
      }
      affected(changes) {
        return affecting(changes, this.var);
      }
      value(data) {
        return extract(data, this.var);
      }
    }

    /** Try all classes in the list to parse expression */
    _defineProperty(AssignExpr, "description", "assignment");
    _defineProperty(AssignExpr, "regexp", new RegExp("^" + VARPATH + " = (.+)$"));
    function parseExpr(expr, classes) {
      for (let cls of classes) {
        try {
          return new cls(expr);
        } catch (e) {
          continue;
        }
      }
      let exp = classes.map(c => c.description).join(" or ");
      throw new Error("Invalid expression: \"".concat(expr, "\", expected: ").concat(exp));
    }

    function isValuable(value) {
      return isScalar(value) || isObject(value) || isArray(value) || isHTMLElement(value);
    }
    function isCompound(value) {
      return isPlainObject(value) || isArray(value);
    }

    /**
     * Recursively traverses object, including arrays and generates flatten map of properties.
     * 
     * For nested objects and arrays whole obj and array is inluded in snapshot to check identities,
     * followed by all elements flattened.
     * 
     * yields entries as pairs [ keypath, scalarvalue ]
     */
    function flatten(obj) {
      let prefix = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
      return function* () {
        // yield value, including compound, except top-level
        if (prefix != "" && isValuable(obj)) {
          yield [prefix, isVoid(obj) ? null : obj];
        }

        // recurse into compound
        if (isCompound(obj)) {
          for (let [k, v] of Object.entries(obj)) {
            if (isValuable(v)) yield* flatten(v, prefix ? "".concat(prefix, ".").concat(k) : k);
          }
        }
      }();
    }

    /**
     * Creates flat snapshot of object properties
     * 
     * @returns {Map}
     */
    function snap(obj) {
      return new Map(flatten(obj));
    }

    /**
     * Compares 2 snapshot and returns delta
     * 
     * The delta contains null for deleted values.
     * For nested objects/arrays if contains whole array, and each element flattened 
     *   
     */
    function diff(oldshot, newshot) {
      let changes = new Map();
      let scanned = [];
      let keys = new Set();
      for (let k of oldshot.keys()) keys.add(k);
      for (let k of newshot.keys()) keys.add(k);
      for (let k of keys) {
        if (scanned.some(ak => includes(ak, k))) continue; // skip fields if whole object replaced 
        let oldval = oldshot.get(k),
          newval = newshot.get(k);
        if (newval !== oldval) {
          changes.set(k, newval === undefined ? null : newval); // removed fields
          scanned.push(k);
        }
      }
      return changes;
    }

    let snapshot = new Map();
    const page = {
      update() {
        let newshot = snap(this);
        let changes = diff(snapshot, newshot);
        if (changes.size == 0) return;
        snapshot = newshot;
        emitEvent('update', changes);
      }
    };

    /** onEvent
     *
     * attaches a handler to specified event type
     * auto-prefixes with "ot." to avoid confusion with standard events
     *
     * @param {string} name event type
     * @param {Function} handler a function to be called as handler(data, event)
     *
     */
    function onEvent(name, handler) {
      assertArgs("onEvent", arguments, ['string', 'function']);
      document.body.addEventListener("ot.".concat(name), async ev => {
        await handler(ev.detail, ev);
        page.update();
      });
    }
    function pickArgs(args) {
      if (args.length == 2) {
        return {
          match: args[0],
          handler: args[1]
        };
      } else {
        return {
          match: undefined,
          handler: args[0]
        };
      }
    }
    function onInput() {
      assertArgs("onInput", arguments, ['string', 'function'], ['function']);
      let {
        handler,
        match
      } = pickArgs(arguments);
      if (match !== undefined) {
        onEvent('input', detail => {
          if (detail.name == match) handler(detail.value);
        });
      } else {
        onEvent('input', detail => {
          handler(detail.name, detail.value);
        });
      }
    }
    function onReset(match, handler) {
      try {
        assertArgs("onReset", arguments, ['string', 'function']);
      } catch (e) {
        console.error(e);
        throw new Error("Invalid onReset usage");
      }
      let watch;
      try {
        watch = parseExpr(match, [VarExpr, ObjExpr]);
      } catch (e) {
        console.error(e);
        throw new Error("Invalid onReset usage");
        // throw e;
      }

      onEvent('load', function () {
        handler();
      });
      onEvent('update', function (changes) {
        if (watch.affected(changes)) {
          let val = watch.eval(page);
          if (isVoid(val)) {
            handler();
          }
        }
      });
    }
    function onUpdate() {
      try {
        assertArgs("onUpdate", arguments, ['string', 'function'], ['function']);
      } catch (e) {
        console.error(e);
        throw new Error("Invalid onUpdate usage");
      }
      let {
        handler,
        match
      } = pickArgs(arguments);
      if (match !== undefined) {
        let watch;
        try {
          watch = parseExpr(match, [VarExpr, ObjExpr]);
        } catch (e) {
          console.error(e);
          throw new Error("Invalid onUpdate usage");
        }
        onEvent('update', function (changes) {
          if (watch.affected(changes)) {
            let val = watch.eval(page);
            if (!isVoid(val)) {
              handler(val);
            }
          }
        });
      } else {
        onEvent('update', function (changes) {
          handler(changes);
        });
      }
    }

    const delays = new Set();
    async function delay(time, func) {
      assertArgs("delay", arguments, ['number', 'function'], ['number']);
      let delayed;
      if (func !== undefined) {
        delayed = function delayed() {
          func();
          page.update();
        };
      } else {
        delayed = function noop() {};
      }
      return new Promise((resolve, reject) => {
        let t = setTimeout(() => {
          delayed();
          resolve();
        }, time);
        delays.add(t);
      });
    }
    function delayEvent(time, name, data) {
      assertArgs("delayEvent", arguments, ['number', 'string', 'data'], ['number', 'string']);
      let event = new CustomEvent("ot.".concat(name), {
        detail: data
      });
      let t = setTimeout(() => document.body.dispatchEvent(event), time);
      delays.add(t);
    }
    function cancelDelays() {
      delays.forEach(t => {
        clearTimeout(t);
      });
    }
    function parseArgs(args) {
      if (args.length == 2) {
        return {
          match: args[0],
          handler: args[1]
        };
      } else {
        return {
          match: undefined,
          handler: args[0]
        };
      }
    }
    class Timer {
      constructor() {
        this.source = "timer";
        this.timers = {};
        this.schedule = {};
        this.started = null;
      }
      now() {
        return Math.floor(performance.now() - this.started);
      }
      emitEvent(name) {
        emitEvent('time', {
          source: this.source,
          time: this.now(),
          name
        });
      }
      start(schedule) {
        this.schedule = schedule;
        for (let name in this.schedule) {
          this.startTimer(name);
        }
        this.started = performance.now();
      }
      startTimer(name) {
        let time = this.schedule[name];
        this.timers[name] = window.setTimeout(() => this.emitEvent(name), time);
      }
      stop() {
        for (let name in this.schedule) {
          this.stopTimer(name);
        }
        this.started = null;
      }
      stopTimer(name) {
        window.clearTimeout(this.timers[name]);
        delete this.timers[name];
      }
    }
    class Schedule extends Timer {
      constructor() {
        super();
        this.source = "schedule";
      }
      start(schedule) {
        let reschedule = {};
        let t = 0;
        for (let phase in schedule) {
          reschedule[phase] = t;
          t += schedule[phase];
        }
        super.start(reschedule);
      }
    }
    class Clock extends Timer {
      constructor() {
        super();
        this.source = "clock";
      }
      start(schedule) {
        super.start(schedule);
        // zeroth tick
        for (let name in schedule) {
          this.emitEvent(name);
        }
      }
      startTimer(name) {
        let time = this.schedule[name];
        this.timers[name] = window.setInterval(() => this.emitEvent(name), time);
      }
      stopTimer(name) {
        window.clearInterval(this.timers[name]);
        delete this.timers[name];
      }
    }
    const timer = new Timer();
    function startTimer(alarms) {
      timer.start(alarms);
    }
    function stopTimer(alarm) {
      if (alarm !== undefined) {
        timer.stopTimer(alarm);
      } else {
        timer.stop();
      }
    }
    const schedule = new Schedule();
    function startSchedule(phases) {
      schedule.start(phases);
    }
    function stopSchedule() {
      schedule.stop();
    }
    const clock = new Clock();
    function startClock(ticks) {
      clock.start(ticks);
    }
    function stopClock(tick) {
      if (tick !== undefined) {
        clock.stopTimer(tick);
      } else {
        clock.stop();
      }
    }
    function onTimer() {
      assertArgs("onTimer", arguments, ['string', 'function'], ['function']);
      let {
        handler,
        match
      } = parseArgs(arguments);
      if (match !== undefined) {
        onEvent('time', function (data) {
          if (data.source == 'timer' && data.name == match) handler(data.time);
        });
      } else {
        onEvent('time', function (data) {
          if (data.source == 'timer') handler(data.name, data.time);
        });
      }
    }
    function onTimeout(handler) {
      assertArgs("onTimeout", arguments, ['function']);
      onEvent('time', function (data) {
        if (data.source == "timer" && data.name == "timeout") handler(data.time);
      });
    }
    function onClock() {
      assertArgs("onClock", arguments, ['string', 'function'], ['function']);
      let {
        handler,
        match
      } = parseArgs(arguments);
      if (match !== undefined) {
        onEvent('time', function (data) {
          if (data.source == 'clock' && data.name == match) handler(data.time);
        });
      } else {
        onEvent('time', function (data) {
          if (data.source == 'clock') handler(data.name, data.time);
        });
      }
    }
    function onSchedule() {
      assertArgs("onSchedule", arguments, ['string', 'function'], ['function']);
      let {
        handler,
        match
      } = parseArgs(arguments);
      if (match !== undefined) {
        onEvent('time', function (data) {
          if (data.source == 'schedule' && data.name == match) handler(data.time);
        });
      } else {
        onEvent('time', function (data) {
          if (data.source == 'schedule') handler(data.name, data.time);
        });
      }
    }

    const handlers$1 = {
      'ot.load': function otLoad() {},
      'ot.startIteration': null,
      // required
      'ot.startTrial': null,
      // required
      'ot.completeTrial': null // required
    };

    const handlerNames = {
      'ot.load': 'onLoad',
      'ot.startIteration': 'onIteration',
      'ot.startTrial': 'onTrial',
      'ot.completeTrial': 'onComplete'
    };
    function metaHandler$1(detail, event) {
      let handler = handlers$1[event.type];
      if (!handler) {
        let name = handlerNames[event.type];
        throw new Error("Missing ".concat(name, " handler"));
      }
      handler(detail, event);
    }
    function init$2() {
      onEvent("load", metaHandler$1);
      onEvent("startIteration", metaHandler$1);
      onEvent("startTrial", metaHandler$1);
      onEvent("completeTrial", metaHandler$1);
    }
    function onLoad(handler) {
      assertArgs("onLoad", arguments, ['function']);
      handlers$1["ot.load"] = handler;
    }
    function onIteration(handler) {
      assertArgs("onIteration", arguments, ['function']);
      handlers$1["ot.startIteration"] = handler;
    }
    function onTrial(handler) {
      assertArgs("onTrial", arguments, ['function']);
      handlers$1["ot.startTrial"] = handler;
    }
    function onComplete(handler) {
      assertArgs("onComplete", arguments, ['function']);
      handlers$1["ot.completeTrial"] = handler;
    }
    function startIteration(iter) {
      assertArgs("startIteration", arguments, []);
      emitEvent("startIteration", iter);
    }
    function startTrial(data) {
      assertArgs("startTrial", arguments, ['object']);
      emitEvent("startTrial", data);
    }
    function completeTrial() {
      assertArgs("completeTrial", arguments, []);
      emitEvent("completeTrial");
    }
    function completePage() {
      assertArgs("completePage", arguments, []);
      cancelDelays();
      // give time for some pending updates to fill form fields
      setTimeout(() => document.querySelector("form#form").submit(), 15);
    }

    function loadImage(image) {
      let img;
      if (typeof image == 'string') {
        img = new Image();
        img.src = image;
      } else if (image instanceof HTMLImageElement) {
        img = image;
      }
      if (img.complete) {
        return Promise.resolve(img);
      } else {
        return new Promise((resolve, reject) => {
          img.onload = () => resolve(img);
          img.onerror = reject;
        });
      }
    }

    function freezeInputs() {
      assertArgs("freezeInputs", arguments, []);
      emitEvent("freezeInputs");
    }
    function resetInputs() {
      assertArgs("resetInputs", arguments, []);
      emitEvent("resetInputs");
    }
    function commitInputs(name) {
      assertArgs("commitInputs", arguments, [], ['string']);
      if (name) {
        emitEvent("commitInputs", {
          name
        });
      } else {
        emitEvent("commitInputs");
      }
    }

    function begMark(name) {
      return "otree.".concat(name, ".beg");
    }
    function endMark(name) {
      return "otree.".concat(name, ".end");
    }
    function measureMark(name) {
      return "otree.".concat(name, ".measure");
    }
    function clear(name) {
      performance.clearMarks(begMark(name));
      performance.clearMarks(endMark(name));
      performance.clearMeasures(measureMark(name));
    }
    function begin(name) {
      performance.mark(begMark(name));
    }
    function end(name) {
      performance.mark(endMark(name));
      performance.measure(measureMark(name), begMark(name), endMark(name));
    }
    function get(name) {
      const entry = performance.getEntriesByName(measureMark(name))[0];
      return entry.duration;
    }
    function beginMeasurement() {
      let name = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "response";
      clear(name);
      begin(name);
    }
    function endMeasurement() {
      let name = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "response";
      end(name);
      return get(name);
    }
    function getMeasurement() {
      let name = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "response";
      return get(name);
    }

    function init$1() {
      window._trialSocket.onmessage = function (message) {
        let data = JSON.parse(message.data);
        if (data.type === 'error') {
          console.error("An error occurred processing a trial on the server.");
        } else if (_TRIALS_SSE) {
          _onServerRecvSSE(data);
        } else if (data.type === 'load') {
          _onServerRecvCSE(data);
        }
      };
      window._trialSocket.send(JSON.stringify({
        type: 'load'
      }));
    }
    function _onServerRecvCSE(_ref) {
      let {
        progress
      } = _ref;
      page.progress = progress;
      emitEvent('load');
    }
    function _onServerRecvSSE(_ref2) {
      let {
        is_page_load,
        feedback,
        trial,
        progress
      } = _ref2;
      page.nextTrial = trial;
      page.progress = progress;
      if (is_page_load) {
        emitEvent('load');
      } else {
        page.feedback = feedback;
        completeTrial();
      }
    }
    function sendTrialResponse(data) {
      freezeInputs();
      var msg = {
        type: 'response',
        response: data,
        trial_id: page.trial.id
      };
      window._trialSocket.send(JSON.stringify(msg));
      if (!_TRIALS_SSE) {
        page.progress.completed++;
        page.progress.remaining--;
        completeTrial();
      }
    }
    function getPlayableTrial() {
      // in roundtrip mode, we determine whether we're finished by whether
      // the trial received from the server is non-null.
      // in non-roundrip mode, we look at the progress.completed attribute.

      if (_TRIALS_SSE) {
        return page.nextTrial;
      } else {
        if (page.progress.completed < TRIALS.length) {
          return TRIALS[page.progress.completed];
        }
      }
    }

    const handlers = {};
    function init() {
      if (window.liveSocket === undefined) return;
      window.liveSocket.onmessage = function (message) {
        let messages = JSON.parse(message.data);
        for (const [type, data] of Object.entries(messages)) {
          emitEvent('live', {
            type,
            data
          });
        }
      };
      onEvent('live', metaHandler);
    }
    function metaHandler(detail, event) {
      let handler = handlers[detail.type];
      if (handler === undefined) {
        throw new Error("Missing onLive('".concat(detail.type, "', function) handler"));
      }
      handler(detail.data);
    }
    function onLive(type, handler) {
      if (window.liveSocket === undefined) {
        throw new Error("Missing live socket, the page is not live");
      }
      assertArgs("onLive", arguments, ['string', 'function']);
      handlers[type] = handler;
    }
    function sendLive(type) {
      let data = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;
      if (window.liveSocket === undefined) {
        throw new Error("Missing live socket, the page is not live");
      }
      assertArgs("sendLive", arguments, ['string', 'object'], ['string']);
      window.liveSocket.send(JSON.stringify({
        [type]: data
      }));
    }

    /**
     * Base class for directives.
     *
     * Used by all built-in directives and can be used to create custom directives.
     */
    class otDirectiveBase {
      constructor(elem) {
        this.elem = elem;
        let attrs = Object.fromEntries(Array.from(this.elem.attributes).map(a => [a.name, a.value]));
        try {
          this.init(attrs);
        } catch (e) {
          console.error(e);
          console.error("Failed to init ".concat(this.constructor.name, " at"), this.elem);
        }
        try {
          this.setup();
        } catch (e) {
          console.error(e);
          console.error("Failed to setup ".concat(this.constructor.name, " at"), this.elem);
        }
        this.render();
      }
      init(attrs) {
        throw new Error("Directive miss init(attrs) method");
      }
      setup() {
        throw new Error("Directive miss setup() method");
      }
      lock() {
        let delay = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 15;
        if (this.locked) return false;
        this.locked = true;
        setTimeout(() => {
          this.locked = false;
        }, delay);
        return true;
      }
      render() {
        this.refresh();
      }
      refresh() {
        // ignore
      }
      onElemEvent(type, handler) {
        function wrapped_handler(ev) {
          try {
            handler.call(this, ev.detail, ev);
          } catch (e) {
            console.error(e);
            console.error("Failed to ".concat(type, " ").concat(this.constructor.name, " at"), this.elem);
          }
        }
        this.elem.addEventListener(type, wrapped_handler.bind(this));
      }
      onPageEvent(type, handler) {
        function wrapped_handler(ev) {
          try {
            handler.call(this, ev.detail, ev);
          } catch (e) {
            console.error(e);
            console.error("Failed to ".concat(type, " ").concat(this.constructor.name, " at"), this.elem);
          }
        }
        document.body.addEventListener(type, wrapped_handler.bind(this));
      }
      emitElemEvent(type) {
        let detail = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : undefined;
        let bubbles = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : false;
        let event = new CustomEvent(type, {
          detail,
          bubbles
        });
        setTimeout(() => this.elem.dispatchEvent(event));
      }
    }

    class otAttr extends otDirectiveBase {
      init(attrs) {
        // this.attr_name = ...;
        // this.expr = parseExpr(attrs["ot-attr-..."], [VarExpr]);
        this.value = null;
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
      }
      refresh() {
        if (isVoid(this.value)) {
          this.elem.removeAttribute(this.attr_name);
        } else {
          this.elem.setAttribute(this.attr_name, this.value);
        }
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          this.value = this.expr.eval(page);
          this.refresh();
        }
      }
    }
    class otAttrValue extends otAttr {
      init(attrs) {
        this.attr_name = "value";
        this.expr = parseExpr(attrs["ot-attr-value"], [VarExpr]);
        this.value = null;
      }
    }
    class otAttrMin extends otAttr {
      init(attrs) {
        this.attr_name = "min";
        this.expr = parseExpr(attrs["ot-attr-min"], [VarExpr]);
        this.value = null;
      }
    }
    class otAttrMax extends otAttr {
      init(attrs) {
        this.attr_name = "max";
        this.expr = parseExpr(attrs["ot-attr-max"], [VarExpr]);
        this.value = null;
      }
    }
    class otAttrHeight extends otAttr {
      init(attrs) {
        this.attr_name = "height";
        this.expr = parseExpr(attrs["ot-attr-height"], [VarExpr]);
      }
    }
    class otAttrWidth extends otAttr {
      init(attrs) {
        this.attr_name = "width";
        this.expr = parseExpr(attrs["ot-attr-width"], [VarExpr]);
      }
    }
    class otAttrSrc extends otAttr {
      init(attrs) {
        this.attr_name = "src";
        this.expr = parseExpr(attrs["ot-attr-src"], [VarExpr]);
      }
    }

    /** Base input */
    class otInputBase extends otDirectiveBase {
      init(attrs) {
        this.elem.ot_frozen = false;
        this.locked = false;
      }

      /* should return input value */
      get value() {
        throw new Error("not implemented");
      }

      /* should update internal input value */
      set value(val) {
        throw new Error("not implemented");
      }
      setup() {
        this.onPageEvent("ot.resetInputs", this.onReset);
        this.onPageEvent("ot.freezeInputs", this.onFreeze);
        this.onPageEvent("ot.commitInputs", this.onCommit);
        this.onElemEvent("ot.commitInput", this.onCommit);
        this.onElemEvent("ot.toggleInput", this.onToggle);
        this.onToggle();
      }
      toggle() {
        this.elem.disabled = this.elem.ot_disabled || this.elem.ot_frozen;
        if (this.elem.disabled) {
          this.elem.setAttribute("disabled", "");
          this.elem.blur();
        } else {
          this.elem.removeAttribute("disabled");
        }
      }
      commit() {
        if (this.elem.disabled) return;
        emitEvent('input', {
          name: this.name,
          value: this.value
        });
        upsert(page, this.name, this.value);
        page.update();
      }
      onReset() {
        this.value = null;
        this.elem.ot_frozen = false;
        this.toggle();
      }
      onFreeze() {
        this.elem.ot_frozen = true;
        this.toggle();
      }
      onToggle() {
        this.toggle();
      }
      onCommit(detail) {
        if (detail && detail.name != this.name) return;
        this.commit();
      }
    }

    class otText extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-text"], [VarExpr]);
        this.content = "";
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
      }
      refresh() {
        this.elem.innerText = this.content;
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          this.content = this.expr.eval(page);
          if (isVoid(this.content)) this.content = "";
          this.refresh();
        }
      }
    }

    class otHTML extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-html"], [VarExpr]);
        this.content = "";
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
      }
      refresh() {
        this.elem.innerHTML = this.content;
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          this.content = this.expr.eval(page);
          if (isVoid(this.content)) this.content = "";
          this.refresh();
        }
      }
    }

    class otImg extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-img"], [VarExpr]);
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
      }
      render() {
        // ignore
      }
      refresh() {
        for (let attr of this.elem.attributes) {
          if (attr.name == 'src') continue;
          this.img.setAttribute(attr.name, attr.value);
        }
        this.elem.replaceWith(this.img);
        this.elem = this.img;
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          this.img = this.expr.eval(page);
          if (isVoid(this.img)) this.img = new Image();
          if (!(this.img instanceof HTMLImageElement)) {
            throw new Error("Invalid value of \"".concat(this.expr.var, "\", expected preloaded HTMLImage, use `ot.loadImage`"));
          }
          this.refresh();
        }
      }
    }

    class otClass extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-class"], [VarExpr]);
        this.defaults = Array.from(this.elem.classList);
        this.value = null;
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
      }
      refresh() {
        this.elem.classList.remove(...this.elem.classList);
        if (this.defaults) this.elem.classList.add(...this.defaults);
        if (isVoid(this.value)) return;
        this.elem.classList.add(this.value);
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          this.value = this.expr.eval(page);
          this.refresh();
        }
      }
    }

    class otIf extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-if"], [VarExpr, CmpExpr]);
        this.enabled = false;
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
      }
      refresh() {
        if (!this.enabled) {
          this.elem.setAttribute("hidden", "");
        } else {
          this.elem.removeAttribute("hidden");
        }
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          let value = this.expr.eval(page);
          if (this.expr instanceof VarExpr) {
            this.enabled = !isVoid(value);
          } else {
            this.enabled = value;
          }
          this.refresh();
        }
      }
    }

    class otClick extends otDirectiveBase {
      init(attrs) {
        let expr = attrs['ot-click'];
        if (expr !== undefined && expr !== "") {
          throw new Error("Invalid attribute value: \"".concat(expr, "\", expected: none"));
        }
      }
      setup() {
        this.onElemEvent('click', this.onClick);
      }
      onClick() {
        if (!this.lock()) return;
        if (this.elem.disabled) return;
        this.emitElemEvent("ot.commitInput");
      }
    }
    class otButton extends otClick {
      onClick() {
        if (!this.lock()) return;
        if (this.elem.disabled) return;
        this.emitElemEvent("ot.commitInput");
        this.elem.blur();
      }
    }

    class otKey extends otDirectiveBase {
      init(attrs) {
        this.key = attrs['ot-key'];
        if (this.key.length != 1 && !this.key.match(/[A-Z]\w+/)) {
          throw new Error("Invalid attribute value: \"".concat(this.key, "\", see \"Code values for keyboard\" at developer.mozilla.org"));
        }
      }
      setup() {
        this.onPageEvent("keydown", this.onKey);
      }
      onKey(detail, event) {
        if (!this.lock()) return;
        if (this.elem.disabled) return;
        if (this.key != event.key && this.key != event.code) return;
        event.preventDefault();
        this.emitElemEvent("ot.commitInput");
      }
    }

    class otEmit extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-emit"], [NameExpr]);
        this.name = this.expr.name;
      }
      setup() {
        this.onElemEvent("ot.toggleInput", this.onToggle);
        this.onElemEvent("ot.commitInput", this.onCommit);
      }
      toggle() {}
      onToggle() {
        this.elem.disabled = this.elem.ot_disabled;
        if (this.elem.disabled) {
          this.elem.setAttribute("disabled", "");
        } else {
          this.elem.removeAttribute("disabled");
          this.elem.blur();
        }
      }
      onCommit() {
        if (this.elem.disabled) return;
        emitEvent(this.name);
      }
    }

    /**
     * Generic ot-input="field = value"
     */
    class otInput extends otInputBase {
      init(attrs) {
        super.init(attrs);
        this.expr = parseExpr(attrs['ot-input'], [AssignExpr]);
        this.name = this.expr.var;
      }
      get value() {
        return this.expr.val;
      }
      set value(val) {
        // ignore
      }
    }

    class otInputNative extends otInputBase {
      setup() {
        super.setup();
        if (!this.elem.name) this.elem.name = this.name;
        this.onPageEvent('ot.update', this.onUpdate);
      }
      get value() {
        // empty value means unset
        let val = this.elem.value;
        return val == "" ? null : val;
      }
      set value(val) {
        // setting null value makes field empty, unlike NaN or undefined
        this.elem.value = isVoid(val) ? null : val;
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          this.value = this.expr.value(page);
        }
      }
      onReset() {
        super.onReset();
        if (!this.elem.disabled && this.elem.hasAttribute("autofocus")) {
          setTimeout(() => this.elem.focus());
        }
      }
    }
    class otInputText extends otInputNative {
      init(attrs) {
        super.init(attrs);
        this.expr = parseExpr(attrs['ot-input'], [VarExpr]);
        this.name = this.expr.var;
        if ('autocommit' in attrs) {
          this.autocommit = attrs['autocommit'] != "" ? parseInt(attrs['autocommit']) : 250;
          if (Number.isNaN(this.autocommit)) throw new Error("Invalid autocommit value, expected empty or number of ms");
        } else {
          this.autocommit = false;
        }
        this.autocommit_timer = null;
      }
      setup() {
        super.setup();
        this.onElemEvent('keydown', this.onKey);
        if (this.autocommit) this.onElemEvent('input', this.onInput);
      }
      toggle() {
        super.toggle();
        this.cancelAutocommit();
        if (!this.elem.disabled && this.elem.hasAttribute('autofocus')) {
          setTimeout(() => this.elem.focus());
        }
      }
      scheduleAutocommit() {
        this.autocommit_timer = setTimeout(() => this.commit(), this.autocommit);
      }
      cancelAutocommit() {
        if (this.autocommit_timer) clearTimeout(this.autocommit_timer);
        this.autocommit_timer = null;
      }
      onKey(_, event) {
        if (event.code == "Enter") {
          if (!this.lock()) return;
          event.preventDefault();
          this.commit();
        }
      }
      onInput() {
        this.cancelAutocommit();
        this.scheduleAutocommit();
      }
    }
    class otInputCheck extends otInputNative {
      init(attrs) {
        super.init(attrs);
        this.expr = parseExpr(attrs['ot-input'], [VarExpr]);
        this.name = this.expr.var;
      }
      get value() {
        return this.elem.checked;
      }
      set value(val) {
        this.elem.checked = Boolean(val);
      }
      setup() {
        super.setup();
        this.onElemEvent('change', this.onChange);
      }
      onChange() {
        this.commit();
      }
    }
    class otInputRadio extends otInputNative {
      init(attrs) {
        super.init(attrs);
        this.expr = parseExpr(attrs['ot-input'], [AssignExpr]);
        this.name = this.expr.var;
      }
      get value() {
        return this.elem.checked ? this.expr.val : undefined;
      }
      set value(val) {
        this.elem.checked = val == this.expr.val;
      }
      setup() {
        super.setup();
        this.onElemEvent('change', this.onChange);
      }
      commit() {
        if (!this.elem.checked) return;
        super.commit();
      }
      onChange() {
        this.commit();
      }
    }

    class otEnabled extends otDirectiveBase {
      init(attrs) {
        this.expr = parseExpr(attrs["ot-enabled"], [VarExpr, CmpExpr]);
        this.isinput = 'ot-input' in attrs;
        this.enabled = null;
      }
      setup() {
        this.onPageEvent('ot.update', this.onUpdate);
        if (!this.isinput) {
          // plain elem
          this.onElemEvent("ot.toggleInput", this.onToggle);
        }
      }
      refresh() {
        this.elem.ot_disabled = !this.enabled;
        this.emitElemEvent("ot.toggleInput");
      }
      onUpdate(changes) {
        if (this.expr.affected(changes)) {
          let value = this.expr.eval(page);
          if (this.expr instanceof VarExpr) {
            this.enabled = !isVoid(value);
          } else {
            this.enabled = value;
          }
          this.refresh();
        }
      }

      // toggling plain elements
      onToggle() {
        this.elem.disabled = this.elem.ot_disabled;
        if (this.elem.disabled) {
          this.elem.setAttribute("disabled", "");
        } else {
          this.elem.removeAttribute("disabled");
        }
      }
    }

    const registry = [[otText, "[ot-text]"], [otHTML, "[ot-html]"], [otImg, "img[ot-img]"], [otClass, "[ot-class]"], [otIf, "[ot-if]"], [otAttrValue, "[ot-attr-value]"], [otAttrMin, "[ot-attr-min]"], [otAttrMax, "[ot-attr-max]"], [otAttrHeight, "[ot-attr-height]"], [otAttrWidth, "[ot-attr-width]"], [otAttrSrc, "img[ot-attr-src]"], [otEnabled, "[ot-enabled]"], [otInputText, "input[type=text][ot-input]"], [otInputText, "input[type=number][ot-input]"], [otInputRadio, "input[type=radio][ot-input]"], [otInputCheck, "input[type=checkbox][ot-input]"], [otInput, "[ot-input]:not(input, select)"], [otEmit, "[ot-emit]"], [otKey, "[ot-key]"], [otClick, "[ot-click]"], [otButton, "button[type=button]"]];
    function registerDirective(cls, selector) {
      registry.push([cls, selector]);
    }
    function attachDirective(cls, selector) {
      document.querySelectorAll(selector).forEach(elem => new cls(elem));
    }

    const setters1 = {
      onLoad,
      onIteration,
      onTrial,
      onComplete
    };
    const setters2 = {
      onEvent,
      onInput,
      onReset,
      onUpdate,
      onLive,
      onTimer,
      onClock,
      onSchedule
    };
    function checkIntegrity(ns) {
      for (let h in setters1) {
        if (window[ns][h] !== setters1[h]) {
          console.error("Invalid usage of ".concat(h, ", expected: ").concat(ns, ".").concat(h, "(function)"));
        }
      }
      for (let h in setters2) {
        if (window[ns][h] !== setters2[h]) {
          console.error("Invalid usage of ".concat(h, ", expected: ").concat(ns, ".").concat(h, "(function) or ").concat(ns, ".").concat(h, "(\"name\", function)"));
        }
      }
    }
    window.addEventListener('load', () => {
      registry.forEach(_ref => {
        let [cls, sel] = _ref;
        return attachDirective(cls, sel);
      });
      checkIntegrity('ot');
      init();
      init$1();
      init$2();

      // the loading should be done when trialSocket receives a message.
      // emitEvent("load");
    });

    exports.AssignExpr = AssignExpr;
    exports.CmpExpr = CmpExpr;
    exports.ConstExpr = ConstExpr;
    exports.Expr = Expr;
    exports.NameExpr = NameExpr;
    exports.ObjExpr = ObjExpr;
    exports.VarExpr = VarExpr;
    exports.affecting = affecting;
    exports.assertArgs = assertArgs;
    exports.beginMeasurement = beginMeasurement;
    exports.cancelDelays = cancelDelays;
    exports.clock = clock;
    exports.commitInputs = commitInputs;
    exports.completePage = completePage;
    exports.completeTrial = completeTrial;
    exports.delay = delay;
    exports.delayEvent = delayEvent;
    exports.emitEvent = emitEvent;
    exports.endMeasurement = endMeasurement;
    exports.freezeInputs = freezeInputs;
    exports.getMeasurement = getMeasurement;
    exports.getPlayableTrial = getPlayableTrial;
    exports.init = init$2;
    exports.isArray = isArray;
    exports.isFunction = isFunction;
    exports.isHTMLElement = isHTMLElement;
    exports.isObject = isObject;
    exports.isPlainObject = isPlainObject;
    exports.isScalar = isScalar;
    exports.isVoid = isVoid;
    exports.keypath = keypath;
    exports.loadImage = loadImage;
    exports.onClock = onClock;
    exports.onComplete = onComplete;
    exports.onEvent = onEvent;
    exports.onInput = onInput;
    exports.onIteration = onIteration;
    exports.onLive = onLive;
    exports.onLoad = onLoad;
    exports.onReset = onReset;
    exports.onSchedule = onSchedule;
    exports.onTimeout = onTimeout;
    exports.onTimer = onTimer;
    exports.onTrial = onTrial;
    exports.onUpdate = onUpdate;
    exports.otAttr = otAttr;
    exports.otDirectiveBase = otDirectiveBase;
    exports.otInputBase = otInputBase;
    exports.page = page;
    exports.parseExpr = parseExpr;
    exports.registerDirective = registerDirective;
    exports.resetInputs = resetInputs;
    exports.schedule = schedule;
    exports.sendLive = sendLive;
    exports.sendTrialResponse = sendTrialResponse;
    exports.startClock = startClock;
    exports.startIteration = startIteration;
    exports.startSchedule = startSchedule;
    exports.startTimer = startTimer;
    exports.startTrial = startTrial;
    exports.stopClock = stopClock;
    exports.stopSchedule = stopSchedule;
    exports.stopTimer = stopTimer;
    exports.timer = timer;

    return exports;

})({});
