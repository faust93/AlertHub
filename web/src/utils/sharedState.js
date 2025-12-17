import { ref } from 'vue'

export const menuCollapsed = ref(false)

const ftsSearch = ref('')
const ftsFilterUpd = ref(false)

const savedUpdFunc = ref()
function savedSearchRefresh() {
    savedUpdFunc.value()
}

function ftsSearchSet(newVal) {
  ftsSearch.value = newVal
}

export function ftsSearchRef() {
  return {
    ftsSearch,
    ftsSearchSet,
    ftsFilterUpd,
    savedSearchRefresh,
    savedUpdFunc
  }
}
