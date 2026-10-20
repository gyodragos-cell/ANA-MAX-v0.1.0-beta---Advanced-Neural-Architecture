'use strict';

/*
 * OS29 Frida trace template. It does not choose a process or hook automatically.
 * The Python bridge attaches only to a process name explicitly approved in lab_scope.json.
 * Only method timing, argument types, return type and exception class are emitted;
 * argument values, object contents, credentials and return values are deliberately omitted.
 */
const state = { traceId: null, className: null, methodName: null, hooked: 0, seq: 0 };

function validId(value) {
  return typeof value === 'string' && /^[A-Za-z0-9_.:-]{1,128}$/.test(value);
}

function emit(kind, action, outcome, attrs, durationMs, parentEventId) {
  if (!state.traceId) return null;
  state.seq += 1;
  const event = {
    schema_version: 'os29.trace.v1',
    event_id: 'frida-' + Date.now().toString(36) + '-' + state.seq.toString(36) + '-' + Math.random().toString(36).slice(2, 7),
    trace_id: state.traceId,
    parent_event_id: parentEventId || null,
    timestamp: new Date().toISOString(),
    source: 'frida',
    component: state.className || 'unconfigured',
    kind: kind,
    action: action,
    outcome: outcome,
    duration_ms: typeof durationMs === 'number' && durationMs >= 0 ? durationMs : null,
    attributes: attrs || {}
  };
  send({ type: 'os29.trace', event: event });
  return event.event_id;
}

rpc.exports = {
  settraceid: function (traceId) {
    if (!validId(traceId)) throw new Error('invalid trace_id format');
    state.traceId = traceId;
    return true;
  },

  configure: function (config) {
    if (!config || typeof config.className !== 'string' ||
        typeof config.methodName !== 'string' ||
        !config.className.trim() || !config.methodName.trim()) {
      throw new Error('exact className and methodName are required');
    }
    state.className = config.className;
    state.methodName = config.methodName;

    return new Promise(function (resolve, reject) {
      Java.perform(function () {
        try {
          const Target = Java.use(state.className);
          const method = Target[state.methodName];
          if (!method || !method.overloads || method.overloads.length < 1) {
            throw new Error('target method was not found');
          }
          method.overloads.forEach(function (overload, overloadIndex) {
            const original = overload;
            const argumentTypes = overload.argumentTypes.map(function (t) { return t.className; });
            const returnType = overload.returnType.className;
            original.implementation = function () {
              const started = Date.now();
              state.seq += 1;
              const spanId = 'span-' + Date.now().toString(36) + '-' + state.seq.toString(36);
              const enterEventId = emit('frida.method.enter', state.methodName, 'observed', {
                span_id: spanId,
                overload_index: overloadIndex,
                argument_count: arguments.length,
                argument_types: argumentTypes
              });
              try {
                const result = original.apply(this, arguments);
                emit('frida.method.exit', state.methodName, 'success', {
                  span_id: spanId,
                  overload_index: overloadIndex,
                  return_type: returnType
                }, Date.now() - started, enterEventId);
                return result;
              } catch (error) {
                const exceptionType = error && error.$className ? String(error.$className) : 'JavaThrowable';
                emit('frida.method.exit', state.methodName, 'error', {
                  span_id: spanId,
                  overload_index: overloadIndex,
                  exception_type: exceptionType
                }, Date.now() - started, enterEventId);
                throw error;
              }
            };
            state.hooked += 1;
          });
          resolve({ hooked_overloads: state.hooked, className: state.className, methodName: state.methodName });
        } catch (error) {
          reject(String(error));
        }
      });
    });
  }
};