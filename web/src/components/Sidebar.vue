<template>
<el-aside :width="menuCollapsed ? '64px' : '200px'" style="transition: width 0.2s;">
  <el-menu :router=true :collapse="menuCollapsed" :default-active="$route.path"
    class="el-menu-vertical"
    background-color="#eef1f6"
    mode="vertical">
    <el-menu-item index="/home/dashboard">
      <el-icon :size="20">
        <PieChart />
      </el-icon>
      <span>Dashboard</span>
    </el-menu-item>
    <el-menu-item index="/home/alerts">
      <el-icon :size="20">
        <Bell />
      </el-icon>
      <span>Alerts</span>
    </el-menu-item>
    <el-menu-item index="/home/schedules">
      <el-icon>
        <Calendar />
      </el-icon>
      <span>OnCall</span>
    </el-menu-item>
    <el-menu-item index="/home/maintenance">
      <el-icon>
        <MuteNotification />
      </el-icon>
      <span>Maintenance</span>
    </el-menu-item>
    <el-sub-menu index="1">
      <template #title>
        <el-icon :size="20">
          <Setting />
        </el-icon>
        <span>Settings</span>
      </template>
      <el-menu-item index="/home/users">
        <el-icon>
          <User />
        </el-icon>
        Users
      </el-menu-item>
      <el-menu-item index="/home/templates">
        <el-icon>
          <ChatLineSquare />
        </el-icon>
        Templates
      </el-menu-item>
      <el-menu-item index="/home/pipelines">
        <el-icon>
          <Guide />
        </el-icon>
        Pipelines
      </el-menu-item>
    </el-sub-menu>

    <el-sub-menu index="2" >
      <template #title>
        <el-icon :size="20">
          <Search />
        </el-icon>
        <span>Saved Searches</span>
        </template>
        <div v-for="(item, index) in searchFilters" :key="index" class="fts">
          <div v-if="item.user_id === userId || item.shared === 1">
            <el-button size="small" text :icon="Edit" @click="updateFilter(index)" />
            <el-button size="small" class="fts-name" text @click="setFilter(index)">{{ item.name }}</el-button>
          </div>
        </div>
    </el-sub-menu>
  </el-menu>
</el-aside>

  <el-dialog v-model="dialogUpdateSearch" title="Update search query" width="500">
    <el-form ref="searchFormRef" :model="searchForm" :rules="searchFormRules" label-width="auto">
      <el-form-item label="Name" prop="name">
        <el-input v-model="searchForm.name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Query" prop="query">
        <el-input v-model="searchForm.query" type="textarea" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Shared" prop="shared">
        <el-checkbox v-model="searchForm.shared" label="Share with other users" />
      </el-form-item>
    </el-form>
    <el-text class="mx-1" tag="p" size="small"><strong>Created by:</strong> {{ searchForm.user_id }}</el-text>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogUpdateSearch = false">Cancel</el-button>
        <el-button type="danger" @click="submitSearchDelete(searchFormRef)">Delete</el-button>
        <el-button type="primary" @click="submitSearchForm(searchFormRef)">Update</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Setting, Bell, Search, Edit, User, Calendar, Guide, OfficeBuilding, PieChart, ChatLineSquare, MuteNotification } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ftsSearchRef, menuCollapsed } from '@/utils/sharedState'
import { SearchLoad, SearchSave, SearchUpdate, SearchDelete } from '@/request/api'

const router = useRouter()
const { ftsSearch, ftsSearchSet, ftsFilterUpd, savedSearchRefresh, savedUpdFunc } = ftsSearchRef()

const userRole = localStorage.getItem('user_role') || ''
const userId = localStorage.getItem('user_id') || ''

const dialogUpdateSearch = ref(false)

const searchFormRef = ref()
const searchForm = reactive({
  id: 0,
  name: '',
  query: '',
  shared: false,
  user_id: ''
})

const searchFilters = ref([])

const searchFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  query: [{ required: true, message: 'Query is required', trigger: 'blur' }],
})

savedUpdFunc.value = () => { fetchSearchFilters() }

const submitSearchForm = (formEl) => {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await SearchUpdate({
            id: searchForm.id,
            name: searchForm.name,
            query: searchForm.query,
            shared: searchForm.shared,
            user_id: localStorage.getItem('user_id')
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Updated successfully');
            dialogUpdateSearch.value = false;
            fetchSearchFilters()
      } else {
            ElMessage.error('Error updating search query');
      }
    } else {
        ElMessage.error('Error updating search query');
        console.warn('Form validation failed')
    }
  })
}

const submitSearchDelete = async (formEl) => {
    if (!formEl) return
    let res = await SearchDelete(searchForm.id)
    if ('msg' in res && res.msg === "ok") {
        ElMessage.success('Deleted successfully');
        dialogUpdateSearch.value = false;
        fetchSearchFilters()
     } else {
        ElMessage.error('Error removing search query');
     }
}

const fetchSearchFilters = async () => {
        let res = await SearchLoad()
        searchFilters.value = res
}

function setFilter(idx) {
    ftsSearchSet(searchFilters.value[idx].query)
    if (router.currentRoute.value.path != '/home/alerts') {
      router.push('/home/alerts')
    } else {
      ftsFilterUpd.value = true
    }
  }

function updateFilter(idx) {
    searchForm.id = searchFilters.value[idx].id
    searchForm.user_id = searchFilters.value[idx].user_id
    searchForm.name = searchFilters.value[idx].name
    searchForm.query = searchFilters.value[idx].query
    searchForm.shared = searchFilters.value[idx].shared == 1 ? true : false
    dialogUpdateSearch.value = true
}

onMounted(async () => {
    fetchSearchFilters()
})

</script>

<style scoped>
.el-menu-vertical {
  height: 96vh;
  border-right: 1;
  flex-grow: 1;
  background-color: rgb(238, 241, 246);
}

.fts {
  display: flex;
  justify-content: left;
  /* padding: 1px 10px; */
  background-color: rgb(238, 241, 246);
  white-space: nowrap;
}

.fts-name {
  justify-content: flex-start;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 190px;
}

</style>