<template>
<div style="padding: 10px;">
  <el-tabs v-model="activeTab" @tab-click="">
  <el-tab-pane label="Schedules" name="schedules">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="margin: 0;">Schedules</h3>
        <el-button type="primary"
        @click="onAddSchedule()">Add</el-button>
    </div>
    <div>
      <TimeGrid
        :events="timeline_items"
        :groups="timeline_groups"
        :startDate="timelineMinMax.start"
        :endDate="timelineMinMax.end"
        :initialDayWidth="40"
        :groupHeaderHeight="25"
        :trackHeight="30"
        @event-click="onTimelineClick"
        ref="timelineRef"
      />
    </div>
    <div>
    <el-table :data="schedules" style="width: 100%; height: calc(100vh - 595px); overflow: auto;" @filter-change="onFilterChange">
      <el-table-column label="Schedule Name" prop="name" width="210" sortable>
        <template #default="scope">
        {{ scope.row.name }}
        </template>
      </el-table-column>
      <el-table-column label="OnCall Group" prop="group" width="210"
        sortable
        :filters="groupFilters()"
        :filter-method="groupFilter"
        column-key="group"
        >
        <template #default="scope">
            <div>
            <el-tag style="margin-right: 4px">
            {{ parseGroup(scope.row.group_id) }}
            </el-tag>
            </div>
        </template>
      </el-table-column>
      <el-table-column label="Active Period" prop="starts_at" width="380" sortable>
        <template #default="scope">
        <div style="display: flex; align-items: center">
        <el-icon><timer /></el-icon>
        <span style="margin-left: 10px">{{ convertIsoToCustomFormat(scope.row.starts_at) }} - {{ convertIsoToCustomFormat(scope.row.ends_at) }}</span>
        </div>
        </template>
      </el-table-column>
      <el-table-column label="Mute Hours" prop="mute_starts" width="180">
        <template #default="scope">
        <div style="display: flex; align-items: center">
        <el-icon><timer /></el-icon>
        <span style="margin-left: 10px">{{ scope.row.mute_starts }} - {{ scope.row.mute_ends }}</span>
        </div>
        </template>
      </el-table-column>
      <el-table-column label="Assigned People" prop="people" width="180" sortable>
        <template #default="scope">
            <div>
            <el-tag
                v-for="(person, idx) in parsePeople(scope.row.people)"
                :key="idx"
                style="margin-right: 4px"
            >
            {{ person }}
            </el-tag>
            </div>
        </template>
      </el-table-column>
      <el-table-column label="Operations">
       <template #default="scope">
        <el-button size="small" :icon="Edit"
        @click="onUpdateSchedule(scope.row.id)"/>
        <el-button size="small" :icon="Delete"
          type="danger"
          @click="onDeleteSched(scope.row.id)"
          />
       </template>
     </el-table-column>
    </el-table>
    </div>
  </el-tab-pane>
  <!-- Groups -->
  <el-tab-pane label="Groups" name="groups">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="margin: 0;">OnCall Groups</h3>
        <el-button type="primary"
        @click="onAddScheduleGroup()">Add</el-button>
    </div>
    <el-table :data="scheduleGroups" style="width: 100%; height: calc(100vh - 240px); overflow: auto;">
      <el-table-column label="Name" prop="name" width="210">
        <template #default="scope">
        {{ scope.row.name }}
        </template>
      </el-table-column>
      <el-table-column label="Assigned Pipeline" prop="pipeline" width="210">
        <template #default="scope">
            <el-tag style="margin-right: 4px">
            {{ parsePipeline(scope.row.pipeline_id) }}
            </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Assigned Team" prop="team" width="210">
        <template #default="scope">
            <el-tag style="margin-right: 4px">
            {{ parseTeam(scope.row.team_id) }}
            </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Operations">
       <template #default="scope">
        <el-button size="small" :icon="Edit"
        @click="onUpdateScheduleGroup(scope.row.id)"/>
        <el-button size="small" :icon="Delete"
          type="danger"
          @click="onDeleteScheduleGroup(scope.row.id)"
          />
       </template>
     </el-table-column>
    </el-table>
  </el-tab-pane>
  </el-tabs>
</div>
<!-- Add schedule dialog -->
<el-dialog
    v-model="dialogAddSched"
    :title="schedFormTitle"
    width="700"
    :modal="false">
    <el-form
      ref="addSchedFormRef"
      :model="addSchedForm"
      label-width="auto"
      :rules="addSchedFormRules"
      label-position="top"
      >
      <el-form-item label="Schedule name" prop="name" >
        <el-input v-model="addSchedForm.name" autocomplete="off" placeholder="Specify schedule name" />
      </el-form-item>
      <el-form-item label="OnCall group" prop="group_id" >
            <el-cascader
                v-model="selectedGroup"
                placeholder="Schedule assigned oncall group"
                :options="schedGroups"
                :props="{ multiple: false }"
                filterable
                clearable
                style="width: 100%;"
            />
      </el-form-item>
      <el-form-item label="Assigned people" prop="people" >
            <el-cascader
                v-model="selectedUsers"
                placeholder="Schedule assigned user"
                :options="team_users"
                :props="{ multiple: true }"
                :show-all-levels="true"
                filterable
                clearable
                style="width: 100%;"
            />
       </el-form-item>
      <el-form-item label="Schedule Time" prop="range">
        <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="To"
            start-placeholder="Start date"
            end-placeholder="End date"
            :showWeekNumber="true"
        />
      </el-form-item>
      <el-form-item label="Mute hours" >
        <el-time-select
            v-model="startTime"
            style="width: 140px"
            class="mr-4"
            placeholder="Start time"
            start="00:00"
            step="00:10"
            end="23:59"
        />-
        <el-time-select
            v-model="endTime"
            style="width: 140px"
            placeholder="End time"
            start="00:00"
            step="00:10"
            end="23:59"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogAddSched = false">Cancel</el-button>
        <el-button type="primary" @click="submitAddSchedForm(addSchedFormRef)">Save</el-button>
      </div>
    </template>
</el-dialog>
<!-- Group dialog -->
<el-dialog
    v-model="dialogAddSchedGroup"
    :title="groupFormTitle"
    width="500"
    :modal="false">
    <el-form
      ref="addSchedGroupFormRef"
      :model="addSchedGroupForm"
      :rules="addSchedGroupFormRules"
      label-width="auto">
      <el-form-item label="Name" prop="name" >
        <el-input v-model="addSchedGroupForm.name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Team" prop="team_id" >
            <el-cascader
                v-model="selectedTeam"
                placeholder="Assign Team here"
                :options="teams"
                :props="{ multiple: false }"
                filterable
                style="width: 100%;"
            />
      </el-form-item>
      <el-form-item label="Pipeline" prop="pipeline_id" >
            <el-cascader
                v-model="selectedPipeline"
                placeholder="Specify Pipeline"
                :options="pipelines"
                :props="{ multiple: false }"
                filterable
                style="width: 100%;"
            />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogAddSchedGroup = false">Cancel</el-button>
        <el-button type="primary" @click="submitAddSchedGroupForm(addSchedGroupFormRef)">Save</el-button>
      </div>
    </template>
</el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Delete, Timer, Edit } from '@element-plus/icons-vue'
import { GetUsers, GetTeams, AddSchedule, UpdateSchedule, DeleteSchedule, GetSchedules, GetScheduleGroups, AddScheduleGroup, DeleteScheduleGroup, UpdateScheduleGroup, GetPipelines } from '@/request/api.js'
import { ElMessage } from 'element-plus'
import { convertIsoToCustomFormat, convertEpochToCustomFormat } from '@/utils/utils'
import TimeGrid from '@/components/TimeGrid.vue'

const userRole = ref(localStorage.getItem('user_role') || '')

const activeTab = ref('schedules')

const schedules = ref([])
const scheduleGroups = ref([])

const timelineRef = ref()
const dialogAddSchedGroup = ref(false)
const addSchedGroupFormRef = ref()
const addSchedGroupForm = reactive({
  id: '',
  name: '',
  pipeline_id: 0,
  team_id: 0
})
const addSchedGroupFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  pipeline_id: [{ required: true, message: 'Pipeline is required', trigger: 'blur' }],
  team_id: [{ required: true, message: 'Team is required', trigger: 'blur' }],
})

const dialogAddSched = ref(false)
const addSchedFormRef = ref()
const addSchedForm = reactive({
  id: '',
  name: '',
  group_id: 0,
  starts_at: '',
  ends_at: '',
  mute_starts: '',
  mute_ends: '',
  people: '',
  range: ''
})

const checkRange = (rule, value, callback) => {
  if (timeRange.value?.length <= 0) {
    return callback(new Error('Please specify time range'))
  } else {
    callback()
  }
}
const addSchedFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' },
        { min: 3, max: 40, message: 'Length should be 3 to 40', trigger: 'blur' },
  ],
  group_id: [{ required: true, message: 'Group is required', trigger: 'blur' }],
  range: [{ validator: checkRange, trigger: 'change' }],
})

const timeRange = ref('')
const startTime = ref('')
const endTime = ref('')

const schedGroups = ref()
const users = ref([])
const teams = ref([])

const selectedGroup = ref([])
const selectedUsers = ref([])

const pipelines = ref([])
const selectedPipeline = ref([])
const selectedTeam = ref([])

const team_users = computed(() => {
  const grpItem = scheduleGroups.value.find(
    item => item.id === selectedGroup.value?.[0]
  )
  if (!grpItem) return []

  const team = teams.value.find(t => t.value === grpItem.team_id)
  if (!team) return []

  return team.members
    .map(id => users.value.find(u => u.value === id))
    .filter(Boolean)
    .map(user => ({ value: user.value, label: user.label }))
})

let groupFormTitle = ''
let schedFormTitle = ''
let submitAddSchedForm
let submitAddSchedGroupForm

const timelineMinMax = ref({ start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), end: new Date(Date.now() + 120 * 24 * 60 * 60 * 1000 ) })
const timeline_groups = ref([])

const timeline_items = ref([])
//{ group: 'group1', type: 'range', name: "kek", start: 1707135072000, end: 1708431072000, cssVariables: { '--item-background': 'var(--color-4)' } },

/* Schedules */
function funcAddSchedForm(formEl) {
    if (!formEl) return;
    if(timeRange.value.length) {
        addSchedForm.starts_at = timeRange.value[0].toISOString()
        addSchedForm.ends_at = timeRange.value[1].toISOString()
    }
    if(startTime.value.length && endTime.value.length) {
        addSchedForm.mute_starts = startTime.value
        addSchedForm.mute_ends = endTime.value
    }
    let ids
    if(selectedUsers.value) {
        ids = selectedUsers.value.map(item => item[0])
        addSchedForm.people = JSON.stringify(ids)
    }
    if(selectedGroup.value) {
      addSchedForm.group_id = selectedGroup.value[0]
    } else {
      addSchedForm.group_id = 0
    }
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await AddSchedule({
            name: addSchedForm.name,
            group_id: addSchedForm.group_id,
            starts_at: addSchedForm.starts_at,
            ends_at: addSchedForm.ends_at,
            mute_starts: addSchedForm.mute_starts,
            mute_ends: addSchedForm.mute_ends,
            people: addSchedForm.people,
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully')
            dialogAddSched.value = false
            timeRange.value = ''
            fetchSchedules()
      } else {
            ElMessage.error('Error adding schedule')
      }
    } else {
        ElMessage.error('Error adding schedule')
    }
  })
}

function funcUpdateSchedForm(formEl) {
    if (!formEl) return;
    if(timeRange.value.length) {
        addSchedForm.starts_at = timeRange.value[0].toISOString()
        addSchedForm.ends_at = timeRange.value[1].toISOString()
    }
    if(startTime.value.length && endTime.value.length) {
        addSchedForm.mute_starts = startTime.value
        addSchedForm.mute_ends = endTime.value
    }
    let ids
    if(selectedUsers.value) {
        ids = selectedUsers.value.map(item => item && item[0])
        addSchedForm.people = JSON.stringify(ids)
    }
    if(selectedGroup.value) {
      addSchedForm.group_id = selectedGroup.value[0]
    } else {
      addSchedForm.group_id = 0
    }
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await UpdateSchedule({
            id: addSchedForm.id,
            name: addSchedForm.name,
            group_id: addSchedForm.group_id,
            starts_at: addSchedForm.starts_at,
            ends_at: addSchedForm.ends_at,
            mute_starts: addSchedForm.mute_starts,
            mute_ends: addSchedForm.mute_ends,
            people: addSchedForm.people,
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully')
            dialogAddSched.value = false
            timeRange.value = ''
            fetchSchedules()
      } else {
            ElMessage.error('Error adding schedule')
      }
    } else {
        ElMessage.error('Error adding schedule')
    }
  })
}

async function onDeleteSched(params) {
  let res = await DeleteSchedule(params)
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Deleted successfully');
    fetchSchedules()
  } else {
     ElMessage.error('Error deleting schedule');
  }
}

function onAddSchedule(){
    schedFormTitle = "Add Schedule"
    submitAddSchedForm = funcAddSchedForm
    addSchedForm.name = ''
    addSchedForm.group_id = ''
    addSchedForm.mute_starts = ''
    addSchedForm.mute_ends = ''
    addSchedForm.people = ''
    startTime.value = ''
    endTime.value = ''
    selectedUsers.value = []
    selectedGroup.value = []
    timeRange.value = []
    dialogAddSched.value = true
}

function onUpdateSchedule(sid){
    schedFormTitle = "Update Schedule"
    submitAddSchedForm = funcUpdateSchedForm
    let sched = schedules.value.filter(item => item.id === sid)[0]
    if (!sched) return
    addSchedForm.id = sched.id
    addSchedForm.name = sched.name
    addSchedForm.group_id = sched.group_id
    addSchedForm.mute_starts = sched.mute_starts
    startTime.value = sched.mute_starts
    addSchedForm.mute_ends = sched.mute_ends
    endTime.value = sched.mute_ends
    selectedUsers.value = sched.people.map(item => [item])
    selectedGroup.value = [sched.group_id]
    timeRange.value = []
    timeRange.value[0] = new Date(sched.starts_at)
    timeRange.value[1] = new Date(sched.ends_at)
    dialogAddSched.value = true
}

/* Schedule Groups */
function funcAddSchedGroupForm(formEl) {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      if(selectedPipeline.value) {
        addSchedGroupForm.pipeline_id = selectedPipeline.value[0]
      } else {
        addSchedGroupForm.pipeline_id = 0
      }
      if(selectedTeam.value) {
        addSchedGroupForm.team_id = selectedTeam.value[0]
      } else {
        addSchedGroupForm.team_id_id = 0
      }
      let res = await AddScheduleGroup({
            name: addSchedGroupForm.name,
            pipeline_id: addSchedGroupForm.pipeline_id,
            team_id: addSchedGroupForm.team_id,
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogAddSchedGroup.value = false;
            fetchSchedules()
      } else {
            ElMessage.error('Error adding group');
      }
    } else {
        ElMessage.error('Error adding group');
    }
  })
}

function onUpdateSchedGroupForm(formEl) {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      if(selectedPipeline.value) {
        addSchedGroupForm.pipeline_id = selectedPipeline.value[0]
      } else {
        addSchedGroupForm.pipeline_id = 0
      }
      if(selectedTeam.value) {
        addSchedGroupForm.team_id = selectedTeam.value[0]
      } else {
        addSchedGroupForm.team_id_id = 0
      }
      let res = await UpdateScheduleGroup({
        id: addSchedGroupForm.id,
        name: addSchedGroupForm.name,
        pipeline_id: addSchedGroupForm.pipeline_id,
        team_id: addSchedGroupForm.team_id,
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogAddSchedGroup.value = false;
            fetchSchedules()
      } else {
            ElMessage.error('Error adding group');
      }
    } else {
        ElMessage.error('Error adding group');
    }
  })
}

function onAddScheduleGroup() {
  groupFormTitle = 'Add Group'
  addSchedGroupForm.name = ''
  addSchedGroupForm.pipeline_id = 0
  submitAddSchedGroupForm = funcAddSchedGroupForm
  dialogAddSchedGroup.value = true
  fetchSchedules()
}

async function onDeleteScheduleGroup(gid) {
  let res = await DeleteScheduleGroup(gid)
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Deleted successfully');
    fetchSchedules()
  } else {
     ElMessage.error('Error deleting a user');
  }
}

function onUpdateScheduleGroup(sid){
    groupFormTitle = "Update Group"
    submitAddSchedGroupForm = onUpdateSchedGroupForm
    let sched = scheduleGroups.value.filter(item => item.id === sid)[0]
    if (!sched) return
    addSchedGroupForm.id = sched.id
    addSchedGroupForm.name = sched.name
    addSchedGroupForm.pipeline_id = sched.pipeline_id
    addSchedGroupForm.team_id = sched.team_id
    selectedPipeline.value = [sched.pipeline_id]
    selectedTeam.value = [sched.team_id]
    dialogAddSchedGroup.value = true
}

async function fetchSchedules() {
  await fetchPipelines()
  await fetchScheduleGroups()
  let res = await GetSchedules()
  schedules.value = res
  setTimeline()
}

async function fetchScheduleGroups() {
  let res = await GetScheduleGroups()
  scheduleGroups.value = res
  schedGroups.value = res.map((sch, idx) => ({
    value: sch.id,
    label: sch.name
  }))
}

async function fetchUsers() {
  let res = await GetUsers()
  users.value = res.map((user, idx) => ({
    value: user.id,
    label: user.name
  }))
}

async function fetchTeams() {
  let res = await GetTeams()
  teams.value = res.map((team, idx) => ({
    value: team.id,
    label: team.name,
    members: team.members
  }))
}

async function fetchPipelines() {
  let res = await GetPipelines()
  pipelines.value = res.map((pipeline, idx) => ({
    value: pipeline.id,
    label: pipeline.name
  }))
}

function parsePipeline(pId) {
  const pipe = pipelines.value.find(g => g.value == pId)
  return pipe ? pipe.label : '-'
}

function parseGroup(groupId) {
  const group = schedGroups.value.find(g => g.value == groupId)
  return group ? group.label : '?'
}

function parsePeople(people) {
    if (!people[0]) return []
    return people.map(id => {
           const user = users.value.find(u => u.value === id)
            return user ? user.label : id
            })
}

function parseTeam(teamId) {
  const team = teams.value.find(t => t.value === teamId)
  return team ? team.label : '-'
}

function convertToUTC(dateString) {
    const date = new Date(dateString);
    const timezoneMatch = dateString.match(/([+-]\d{2}):(\d{2})$/);
    if (timezoneMatch) {
        const hours = parseInt(timezoneMatch[1]);
        const minutes = parseInt(timezoneMatch[2]);
        const offsetMinutes = hours * 60 + (hours < 0 ? -minutes : minutes);
        date.setMinutes(date.getMinutes() + offsetMinutes);
    }
    return date;
}

function setTimeline() {
  let start = new Date()
  start.setHours(0, 0, 0, 0)
  start.setDate(start.getDate() - 30)
  let end = new Date()
  end.setHours(0, 0, 0, 0)
  end.setDate(end.getDate() + 120)
  timelineMinMax.value.start = start
  timelineMinMax.value.end = end

  timeline_groups.value = schedGroups.value.map((grp, idx) => ({
   id: grp.value,
   name: grp.label
  }))

 /*
  timeline_items.value = schedules.value.map((sch, idx) => ({
    id: sch.id,
    group: 'group1',
    type: 'range',
    name: sch.name,
    cssVariables: { '--height': '10%' },
    start: new Date(sch.starts_at).getTime(),
    end: new Date(sch.ends_at).getTime()
  }))
*/
  timeline_items.value = schedules.value.map((sch, idx) => {
    const startTime = new Date(sch.starts_at)
    const endTime = new Date(sch.ends_at)
    const durationInDays = (endTime - startTime) / (1000 * 60 * 60 * 24)
    const clampedDays = Math.min(durationInDays, 17)
    const hue = 240 - (clampedDays / 10) * 50
    const backgroundColor = `hsl(${hue}, 80%, 40%)`
    return {
        id: sch.id,
        groupId: sch.group_id,
        title: sch.name,
        color: backgroundColor,
        start: startTime,
        end: endTime
    }
  })
  //timelineRef.value.scrollToNow()
}

function onTimelineClick(event) {
    onUpdateSchedule(event.id)
}

function groupFilters() {
  const sch_groups = scheduleGroups.value.map((grp, idx) => ({
   text: grp.name,
   value: grp.id
  })) ?? [{ text: '-', value: '0' }]
  return sch_groups
}

const groupFilter = (value, row) => {
  return row.group_id === value
}

function onFilterChange(grpfilters) {
  const filters = grpfilters['group']
  timeline_groups.value = (filters.length > 0 
    ? schedGroups.value.filter(grp => filters.includes(grp.value))
    : schedGroups.value
  ).map(grp => ({
    id: grp.value,
    name: grp.label
  }))
}

onMounted(async () => {
  fetchUsers()
  fetchTeams()
  fetchSchedules()
})

/*
function teamPeopleParse(){
  const grpItem = scheduleGroups.value.filter(item => item.id === selectedGroup.value[0])[0]
  const tId = grpItem.team_id
  const team = teams.value.find(t => t.value === tId)
  team_users.value = team.members.map(id => {
            const user = users.value.find(u => u.value === id)
            return user ? {"value": user.value, "label": user.label} : {}
            })
}
*/
</script>
