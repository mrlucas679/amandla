// Deaf window wrapper: try to require the project's root signs_library.js when available
if (typeof require !== 'undefined') {
  try {
    module.exports = require('../../../signs_library.js')
  } catch (e) {
    // silent
  }
} else if (typeof window !== 'undefined' && window.AMANDLA_SIGNS) {
  window.AMANDLA_SIGNS_DEAF = window.AMANDLA_SIGNS
}

