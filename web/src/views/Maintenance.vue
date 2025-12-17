<template>
    <div style="padding: 10px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
          <h3 style="margin: 0;">Maintenance Windows</h3>
          <el-button v-if="userRole === '0'" type="primary" @click="onAddMaintenance()">Add</el-button>
        </div>
        <el-table :data="maintenanceData" style="width: 100%; height: calc(100vh - 225px); overflow: auto;">
            <el-table-column label="Name" prop="name" width="210">
                <template #default="scope">
                {{ scope.row.name }}
                </template>
            </el-table-column>
            <el-table-column label="Description" prop="description">
                <template #default="scope">
                {{ scope.row.description }}
                </template>
            </el-table-column>
            <el-table-column label="Maintenance Time" prop="name">
                <template #default="scope">
                <div style="display: flex; align-items: center">
                    <el-icon><timer /></el-icon>
                    <span style="margin-left: 5px">{{ convertIsoToCustomFormat(scope.row.starts_at) }} - {{ convertIsoToCustomFormat(scope.row.ends_at) }}</span>
                </div>
                </template>
            </el-table-column>
            <el-table-column label="OnCall Group" prop="oncall_groups" width="180" sortable>
              <template #default="scope">
                  <div>
                  <el-tag
                      v-for="(person, idx) in parseGroups(scope.row.oncall_groups)"
                      :key="idx"
                      style="margin-right: 4px"
                  >
                  {{ person }}
                  </el-tag>
                  </div>
              </template>
            </el-table-column>
            <el-table-column label="Filter" prop="fiter">
                <template #default="scope">
                {{ scope.row.filter }}
                </template>
            </el-table-column>
           <el-table-column label="Operations">
              <template #default="scope">
                <el-button size="small" :icon="Edit"
                @click="onUpdateMaintenance(scope.row.id)"/>
                <el-button size="small" :icon="Delete"
                type="danger"
                @click="onDeleteMaintenance(scope.row.id)"
                />
              </template>
            </el-table-column>
        </el-table>
    </div>

  <el-dialog v-model="dialogMaintenance" :title="dialogTitle" width="600" :modal="false">
    <el-form ref="addMaintenanceFormRef" label-width="auto" :model="addMaintenanceForm" :rules="addMaintenanceFormRules" label-position="top">
      <el-form-item label="Name" prop="name" >
        <el-input v-model="addMaintenanceForm.name" placeholder="Maintenance Name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Description" prop="description" >
        <el-input v-model="addMaintenanceForm.description" placeholder="Maintenance Description" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Filter Expression" prop="filter" >
        <el-input v-model="addMaintenanceForm.filter" placeholder="Match alerts only by specific criterions, eg. status == 'firing'" autocomplete="off" />
      </el-form-item>
      <el-form-item label="OnCall Group" prop="oncall_groups" >
            <el-cascader
                v-model="selectedGroups"
                placeholder="Attach Maintenance to OnCall group"
                :options="scheduleGroupsOpt"
                :props="{ multiple: true }"
                :show-all-levels="true"
                filterable
                clearable
                style="width: 100%;"
            />
       </el-form-item>
      <el-form-item label="Maintenance Time" prop="range">
        <el-date-picker v-model="timeRange" type="datetimerange" range-separator="-" start-placeholder="Start date"
            end-placeholder="End date"
            @clear="" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogMaintenance = false">Cancel</el-button>
        <el-button type="primary" @click="submitDialogFunc(addMaintenanceFormRef)">Save</el-button>
      </div>
    </template>
  </el-dialog>

</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Delete, Timer, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetMaintenances, AddMaintenance, DeleteMaintenance, UpdateMaintenance, GetScheduleGroups } from '@/request/api.js'
import { convertIsoToCustomFormat } from '@/utils/utils'

const userRole = localStorage.getItem('user_role') || ''
const userId = localStorage.getItem('user_id') || ''

let dialogTitle = ''
let submitDialogFunc

const timeRange = ref('')
const selectedGroups = ref([])
const scheduleGroups = ref([])
const scheduleGroupsOpt = ref([])

const maintenanceData = ref([])

const dialogMaintenance = ref(false)
const maintenanceDtRange = ref([])

const addMaintenanceFormRef = ref()
const addMaintenanceForm = reactive({
  id: 0,
  name: '',
  description: '',
  filter: '',
  oncall_groups: [],
  starts_at: 0,
  ends_at: 0,
  range: 0
})
const checkRange = (rule, value, callback) => {
  if (timeRange.value?.length <= 0) {
    return callback(new Error('Please specify time range'))
  } else {
    callback()
  }
}
const addMaintenanceFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  range: [{ validator: checkRange, trigger: 'change' }],
})

function parseGroups(grps) {
    if (!grps[0]) return []
    return grps.map(id => {
           const group = scheduleGroupsOpt.value.find(g => g.value === id)
            return group ? group.label : '-'
            })
}

function onAddMaintenance() {
    dialogTitle = 'Add Maintenance'
    addMaintenanceForm.name = ''
    addMaintenanceForm.description = ''
    addMaintenanceForm.filter = ''
    addMaintenanceForm.oncall_groups = []
    selectedGroups.value = []
    timeRange.value = ''
    submitDialogFunc = funcAddMaintenance
    dialogMaintenance.value = true
}

function onUpdateMaintenance(mid){
    dialogTitle = "Update Maintenance"
    submitDialogFunc = funcUpdateMaintenance
    const mnt = maintenanceData.value.filter(item => item.id === mid)[0]
    if (!mnt) return
    addMaintenanceForm.id = mnt.id
    addMaintenanceForm.name = mnt.name
    addMaintenanceForm.description = mnt.description
    addMaintenanceForm.filter = mnt.filter
    selectedGroups.value = mnt.oncall_groups.map(item => [item])
    timeRange.value = []
    timeRange.value[0] = new Date(mnt.starts_at)
    timeRange.value[1] = new Date(mnt.ends_at)
    dialogMaintenance.value = true
}

function funcAddMaintenance(formEl) {
    if (!formEl) return;
    if(timeRange.value?.length) {
        addMaintenanceForm.starts_at = timeRange.value[0].toISOString()
        addMaintenanceForm.ends_at = timeRange.value[1].toISOString()
    }
    let ids
    if(selectedGroups.value) {
        ids = selectedGroups.value.map(item => item && item[0])
        addMaintenanceForm.oncall_groups = JSON.stringify(ids)
    }
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await AddMaintenance({
            name: addMaintenanceForm.name,
            description: addMaintenanceForm.description,
            filter: addMaintenanceForm.filter,
            oncall_groups: addMaintenanceForm.oncall_groups,
            starts_at: addMaintenanceForm.starts_at,
            ends_at: addMaintenanceForm.ends_at,
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully')
            dialogMaintenance.value = false
            timeRange.value = ''
            fetchMaintenance()
      } else {
            ElMessage.error('Error adding maintenance')
      }
    } else {
        ElMessage.error('Error adding maintenance')
    }
  })
}

function funcUpdateMaintenance(formEl) {
    if (!formEl) return;
    if(timeRange.value.length) {
        addMaintenanceForm.starts_at = timeRange.value[0].toISOString()
        addMaintenanceForm.ends_at = timeRange.value[1].toISOString()
    }
    let ids
    if(selectedGroups.value) {
        ids = selectedGroups.value.map(item => item && item[0])
        addMaintenanceForm.oncall_groups = JSON.stringify(ids)
    }
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await UpdateMaintenance({
            id: addMaintenanceForm.id,
            name: addMaintenanceForm.name,
            description: addMaintenanceForm.description,
            filter: addMaintenanceForm.filter,
            oncall_groups: addMaintenanceForm.oncall_groups,
            starts_at: addMaintenanceForm.starts_at,
            ends_at: addMaintenanceForm.ends_at,
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully')
            dialogMaintenance.value = false
            timeRange.value = ''
            fetchMaintenance()
      } else {
            ElMessage.error('Error updating maintenance')
      }
    } else {
        ElMessage.error('Error uptating maintenance')
    }
  })
}

async function onDeleteMaintenance(mid) {
  let res = await DeleteMaintenance(mid)
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Deleted successfully');
    fetchMaintenance()
  } else {
     ElMessage.error('Error deleting maintenance');
  }
}

async function fetchMaintenance() {
  const res = await GetMaintenances()
  maintenanceData.value = res
}

async function fetchScheduleGroups() {
  let res = await GetScheduleGroups()
  scheduleGroups.value = res
  scheduleGroupsOpt.value = res.map((sch, idx) => ({
    value: sch.id,
    label: sch.name
  }))
}

onMounted(async () => {
  fetchMaintenance()
  fetchScheduleGroups()
})
</script>

