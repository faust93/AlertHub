<template>
  <div v-if="isMobile" class="mobile-layout">
    <el-row justify="center">
      <el-col :span="13">
        <el-input v-model="ftsSearch" clearable placeholder="Search Filter" @clear="searchAlerts" @change="searchAlerts"
          size="small">
          <template #append>
            <el-button :icon="Search" @click="searchAlerts" size="small" />
          </template>
          <template #prefix>
            <el-dropdown trigger="click">
              <span class="el-dropdown-link">
                <el-icon><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <div v-for="(item, index) in searchFilters" :key="index">
                    <div v-if="item.user_id === userID || item.shared === 1">
                      <el-dropdown-item @click="ftsSearch = item.query; searchAlerts()">{{ item.name
                        }}</el-dropdown-item>
                    </div>
                  </div>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-input>
      </el-col>
      <el-col :span="10" class="timespan-mobile">
        <el-radio-group v-model="queryRange" @change="fetchAlerts" size="small">
          <el-radio-button value="1" label="1d" />
          <el-radio-button value="2" label="1w" />
          <el-radio-button value="3" label="1m" />
        </el-radio-group>
      </el-col>
    </el-row>

    <el-table :data="alertsTable" style="width: 100%; height: calc(100vh - 180px); overflow: auto;"
      :highlight-current-row="false" row-key="alert_id">
      <el-table-column label="Created" prop="startsAt" sortable>
        <template #default="scope">
          <el-card>
            <div class="card-header">
              <el-tag effect="dark" :type="getStatusTag(scope.row.status)" style="margin-right: 5px;">
                {{ scope.row.status }}
              </el-tag>
              <el-text tag="b">{{ scope.row.alertname }}</el-text><br />
              <el-text size="small">🕙 {{ convertIsoToCustomFormat(scope.row.startsAt) }} → </el-text>
              <el-text v-if="scope.row.status === ALERT_STATUS.RESOLVED" size="small">{{ convertIsoToCustomFormat(scope.row.endsAt)
                }}</el-text>
              <el-text v-else size="small">Now</el-text><br/>
              <el-tag effect="light" :type="getSeverityTag(scope.row.labels?.severity || 'none')">
                {{ scope.row.labels?.severity || 'N/A' }}
              </el-tag><br/>
            </div>
            <p v-for="value, key in scope.row.labels" :key="key" class="text item">
              <el-text tag="b">{{ key }}:</el-text> <el-tag size="small" type="info">{{ value }}</el-tag>
            </p><br />
            <p v-for="value, key in scope.row.annotations" :key="key" class="text item">
              <el-text tag="b">{{ key }}: </el-text><el-text> {{ value }}</el-text>
            </p>
            <el-text size="small" type="info">ID: {{ scope.row.alert_id }}</el-text>
            <template #footer>
              <el-button size="small" @click="onAck(scope.row.alert_id, scope.row.status)"
                :type="scope.row.status === ALERT_STATUS.ACKED ? 'primary' : ''"
                :disabled="[ALERT_STATUS.RESOLVED, ALERT_STATUS.MUTED].includes(scope.row.status)">
                Ack
              </el-button>
              <el-button size="small" :type="scope.row.status === ALERT_STATUS.MUTED ? 'danger' : ''"
                @click="onMute(scope.row.alert_id, scope.row.status)">
                Mute
              </el-button>
            </template>
          </el-card>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top: 15px; text-align: right">
      <el-pagination background :pager-count="5" @current-change="onPageChange" @size-change="onSizeChange"
        :current-page="currentPage" :page-sizes="[30, 50, 100]" :page-size="pageSize" layout="total, prev, pager, next"
        :total="total" />
    </div>
  </div>

  <!-- Desktop -->
  <div v-else style="padding: 10px;">
    <h3>Alerts</h3>
    <el-row :gutter="12" style="padding: 10px;">
      <el-col :span="8" style="text-align: right; ">
        <el-input v-model="ftsSearch" placeholder="Search Filter" clearable @clear="searchAlerts" @change="searchAlerts">
          <template #append>
            <el-button :icon="Search" @click="searchAlerts" />
          </template>
          <template #prefix>
            <el-button link type="primary" plain @click="saveSearch">Save</el-button>
          </template>
        </el-input>
      </el-col>
      <el-col :span="2">
        <el-switch v-model="realTimeUpdate" size="small" active-text="Realtime Update" :disabled="historyMode"/>
      </el-col>
      <el-col :span="2">
        <el-tooltip
          class="box-item"
          effect="dark"
          content="Browse alerts history in chronological order"
          placement="top-start"
          :show-after="800"
        >
        <el-switch v-model="historyMode" @change="onHistoryMode" size="small" active-text="History Mode"/>
        </el-tooltip>
      </el-col>
      <el-col :span="5" class="query-radio">
        <el-radio-group v-model="queryRange" @change="fetchAlerts">
          <el-radio-button value="1" label="Last Day" />
          <el-radio-button value="2" label="Week" />
          <el-radio-button value="3" label="Month" />
          <el-radio-button value="4" label="All" />
        </el-radio-group>
      </el-col>
      <el-col :span="7">
        <div style="display: flex; align-items: center; gap: 8px;">
          <el-date-picker v-model="queryDtRange" type="datetimerange" range-separator="-" start-placeholder="Start date"
            end-placeholder="End date"
            @clear="onDtClear" />
          <el-button :icon="Search" type="primary" @click="fetchAlertsRange" />
        </div>
      </el-col>
    </el-row>

    <el-table :data="alertsTable" style="width: 100%; height: calc(100vh - 263px); overflow: auto;"
      :highlight-current-row="true" :row-key="historyMode ? '_id' : 'alert_id'" :expand-row-keys="expandedRowKeys"
      @expand-change="onExpandChange">
      <el-table-column type="expand">
        <template #default="props">
          <el-row :gutter="20" class="alert-details">
            <el-col :span="16">
              <el-descriptions v-if="!historyMode" class="margin-top" title="Alert" :column="2" size="small" border>
                <el-descriptions-item label="Starts At">{{ convertIsoToCustomFormat(props.row.startsAt) }}</el-descriptions-item>
                <el-descriptions-item label="Last Updated">{{ getDurationString(props.row.updatedAt, new Date().toISOString()) }}</el-descriptions-item>
                <el-descriptions-item label="Status">{{ props.row.status }}</el-descriptions-item>
                <el-descriptions-item label="Severity">{{ props.row.severity }}</el-descriptions-item>
              </el-descriptions>
              <el-descriptions class="margin-top" title="Labels" :column="2" size="small" border>
                <div v-for="(val, key) in props.row.labels" :key="key">
                  <el-descriptions-item>
                    <template #label>
                      <div>
                        {{ key }}
                      </div>
                    </template>
                    <div>
                      <el-tag size="default" type="primary">{{ val }}</el-tag>
                    </div>
                  </el-descriptions-item>
                </div>
              </el-descriptions>
              <el-descriptions class="margin-top" title="Annotations" :column="1" size="small" border>
                <div v-for="(val, key) in props.row.annotations" :key="key">
                  <el-descriptions-item>
                    <template #label>
                      <div>
                        {{ key }}
                      </div>
                    </template>
                    <div>
                      {{ val }}
                    </div>
                  </el-descriptions-item>
                </div>
              </el-descriptions>
              <br>
              <el-text class="mx-1" tag="b" size="small">Generator URL: </el-text>
              <el-link :href="props.row.generatorURL" type="info">
                {{ props.row.generatorURL }}<el-icon class="el-icon--right"><icon-view /></el-icon>
              </el-link>
            </el-col>

            <el-col :span="5" v-if="!historyMode">
              <el-text class="mx-1" type="info" size="small" tag="p" @click="copyToClipboard(props.row.alert_id)"><strong>Alert ID:</strong> {{ props.row.alert_id
                }}</el-text>
              <br>
              <el-text tag="b"><el-icon>
                  <Bell />
                </el-icon> Activity Log:</el-text>
              <el-container style="height: 350px;">
                <el-scrollbar>
                  <el-timeline style="max-width: 600px; padding: 8px 10px;">
                    <el-timeline-item center v-for="(activity, index) in alertHistory" :key="index"
                      :timestamp="convertIsoToCustomFormat(activity.timestamp)" :color="getStatusColor(activity.status)">
                      <el-text tag="b" size="small">{{ activity.status.toUpperCase() }}</el-text>
                      <el-card shadow="never" body-style="background-color: #ffefef; padding: 8px; border-radius: 4px;" 
                              v-if="[ALERT_STATUS.FIRING].includes(activity.status)">
                        <el-text tag="p" size="small">Alert starts firing</el-text>
                        <el-text size="small" tag="b">Event Trigger Time: </el-text>
                        <el-text size="small">{{ convertIsoToCustomFormat(activity.event_timestamp) }}</el-text>
                      </el-card>
                     <el-card shadow="never" body-style="background-color: #f0ffef; padding: 8px; border-radius: 8px;" 
                              v-if="[ALERT_STATUS.RESOLVED].includes(activity.status)">
                        <el-text tag="p" size="small">Alert has been resolved</el-text>
                        <el-text size="small" tag="b">Event Trigger Time: </el-text>
                        <el-text size="small">{{ convertIsoToCustomFormat(activity.event_timestamp) }}</el-text>
                      </el-card> 
                      <el-card shadow="never" body-style="background-color: #f0f9ff; padding: 8px; border-radius: 8px;" 
                              v-if="[ALERT_STATUS.MUTED, ALERT_STATUS.UNMUTED, ALERT_STATUS.ACKED, ALERT_STATUS.UNACKED].includes(activity.status)">
                        <el-text size="small">{{ activity.comment }}</el-text>
                      </el-card>
                    </el-timeline-item>
                  </el-timeline>
                </el-scrollbar>
              </el-container>
            </el-col>
          </el-row>
        </template>
      </el-table-column>

      <el-table-column :label="historyMode ? 'Event Time' : 'Created'" prop="startsAt" width="170" sortable>
        <template #default="scope">
          {{ convertIsoToCustomFormat(scope.row.startsAt) }}
        </template>
      </el-table-column>

      <el-table-column :label="historyMode ? 'Alert Id' : '#'" align="center" :width="historyMode ? 150 : 60">
        <template #default="scope">
          <el-tag effect="light" type="info" @click="copyToClipboard(scope.row.alert_id)">
            {{ historyMode ? scope.row.alert_id : scope.row.alert_count }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="Status" align="center" width="90">
        <template #default="scope">
          <el-tag effect="plain" :type="getStatusTag(scope.row.status)">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Severity" align="center" width="90">
        <template #default="scope">
          <el-tag effect="dark" :type="getSeverityTag(scope.row.labels?.severity || 'none')">
            {{ scope.row.labels?.severity || 'N/A' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Alert" width="400">
        <template #default="scope">
          <el-text tag="b">{{ scope.row.alertname }}</el-text>
        </template>
      </el-table-column>

      <el-table-column label="Environment" align="center" width="150">
        <template #default="scope">
          <el-tag size="small" type="info" effect="plain">{{ scope.row.labels?.environment || 'N/A' }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="Summary">
        <template #default="scope">
          {{ scope.row.annotations?.summary || 'N/A' }}
        </template>
      </el-table-column>

      <el-table-column v-if="!historyMode" label="Operations" width="160">
        <template #default="scope">
          <el-button-group>
            <el-tooltip
              class="box-item"
              effect="dark"
              content="Acknowledge Alert"
              placement="top-start"
              :show-after="800"
            >
            <el-button size="small" @click="onAck(scope.row.alert_id, scope.row.status)"
              :type="scope.row.status === ALERT_STATUS.ACKED ? 'primary' : ''"
              :disabled="[ALERT_STATUS.RESOLVED, ALERT_STATUS.MUTED].includes(scope.row.status)" :icon="CircleCheck" />
            </el-tooltip>
            <el-tooltip
              class="box-item"
              effect="dark"
              content="Mute Alert"
              placement="top-start"
              :show-after="800"
            >
            <el-button size="small" :type="scope.row.status === ALERT_STATUS.MUTED ? 'danger' : ''"
              @click="onMute(scope.row.alert_id, scope.row.status)" :icon="Bell" />
            </el-tooltip>
            <el-popconfirm placement="left" :width="100" confirm-button-text="Yes" confirm-button-type="danger"
              cancel-button-text="No" cancel-button-type="primary" title="Delete Alert?"
              @confirm="onDeleteAlert(scope.row.alert_id)">
              <template #reference>
                <el-button size="small" :icon="Delete" plain />
              </template>
            </el-popconfirm>
          </el-button-group>
        </template>
      </el-table-column>

    </el-table>

    <div style="margin-top: 20px; text-align: right">
      <el-pagination @current-change="onPageChange" @size-change="onSizeChange" :current-page="currentPage"
        :page-sizes="[20, 30, 50, 100]" :page-size="pageSize" layout="total, sizes, prev, pager, next, jumper"
        :total="total" />
    </div>
  </div>

  <el-dialog v-model="dialogSearchSave" title="Save search query" width="500">
    <el-form ref="searchFormRef" :model="searchForm" :rules="searchFormRules">
      <el-form-item label="Name" prop="name" label-width="auto">
        <el-input v-model="searchForm.name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Query" prop="query" label-width="auto">
        <el-input v-model="searchForm.query" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Shared" prop="shared" label-width="auto">
        <el-checkbox v-model="searchForm.shared" label="Share with other users" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogSearchSave = false">Cancel</el-button>
        <el-button type="primary" @click="submitSearchForm(searchFormRef)">Save</el-button>
      </div>
    </template>
  </el-dialog>

</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { io } from "socket.io-client"
import { Bell, CircleCheck, Search, Delete, Timer, ArrowDown, ElementPlus, View as IconView } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetAlerts, GetAlertHistory, SetAlertStatus, DeleteAlert, SearchSave, SearchLoad } from '@/request/api.js'
import { convertIsoToCustomFormat, getDurationString } from '@/utils/utils'
import { ftsSearchRef } from '@/utils/sharedState'
import { useDevice } from '@/utils/useDevice'
import { ALERT_STATUS, ALERT_SEVERITY } from '@/utils/constants'

const { isMobile } = useDevice()
const route = useRoute()

const socket = io()
const ws_state = reactive({
  connected: false,
  events: []
})

const userID = ref(localStorage.getItem('user_id') || '')

const loading = ref(false)
const realTimeUpdate = ref(true)
const historyMode = ref(false)

/* paginator vars */
const currentOffset = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchFilters = ref([])

let alertsBuffer = []
let alertsBufferFlushTimer = null

const alertsTable = ref([])
const alertHistory = ref([])

const expandedRowKeys = ref([])

const queryDtRange = ref([])
const queryRange = ref(localStorage.getItem('query_range') || '2')

const { ftsSearch, ftsSearchSet, ftsFilterUpd, savedSearchRefresh } = ftsSearchRef()

watch(ftsFilterUpd, (newVal) => {
  if(newVal) {
   searchAlerts()
   ftsFilterUpd.value = false
  }
})

/* Search query save form */
const dialogSearchSave = ref(false)

const searchFormRef = ref()
const searchForm = reactive({
  id: 0,
  name: '',
  query: '',
  shared: false,
})

const searchFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  query: [{ required: true, message: 'Query is required', trigger: 'blur' }],
})

const submitSearchForm = (formEl) => {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await SearchSave({
            name: searchForm.name,
            query: searchForm.query,
            shared: searchForm.shared,
            user_id: localStorage.getItem('user_id')
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogSearchSave.value = false;
            savedSearchRefresh()
      } else {
            ElMessage.error('Error adding search query');
      }
    } else {
        ElMessage.error('Error adding search query');
        console.warn('Form validation failed')
    }
  })
}

const onDtClear = () => {
  queryRange.value = localStorage.getItem('query_range') || '2'
}

const saveSearch = () => {
    searchForm.query = ftsSearch
    dialogSearchSave.value = true
}

const getStatusColor = (status) => {
  switch (status) {
    case ALERT_STATUS.RESOLVED:
      return '#67C23A'
    case ALERT_STATUS.FIRING:
      return '#F56C6C'
    case ALERT_STATUS.ACKED:
      return '#409eff'
    case ALERT_STATUS.UNACKED:
      return '#409ec0'
    default:
      return 'gray'
  }
}

const getStatusTag = (status) => {
  switch (status) {
    case ALERT_STATUS.RESOLVED:
      return 'success'
    case ALERT_STATUS.FIRING:
      return 'danger'
    case ALERT_STATUS.ACKED:
      return 'primary'
    default:
      return 'info'
  }
}

const getSeverityTag = (status) => {
  switch (status) {
    case ALERT_SEVERITY.WARNING:
      return 'warning'
    case ALERT_SEVERITY.CRITICAL:
      return 'danger'
    default:
      return 'info'
  }
}

const onExpandChange = async (row, expandedRows) => {
  if (historyMode.value) return
  const isExpanded = expandedRows.some(r => r.alert_id === row.alert_id)
  if (isExpanded) {
    expandedRowKeys.value = [row.alert_id]
    alertHistory.value = ""
    const res = await GetAlertHistory(row.alert_id)
    alertHistory.value = res["alert_history"]
  } else {
    expandedRowKeys.value = []
    alertHistory.value = ""
  }
}

const onHistoryMode = async () => {
  ftsSearch.value = ''
  fetchAlerts()
}

const fetchAlertsRange = async () => {
    if(queryDtRange.value.length) {
        queryRange.value = 0
        currentPage.value = 1
    }
    fetchAlerts()
}

const searchAlerts = async () => {
  localStorage.setItem('fts_query', ftsSearch.value)
  fetchAlerts()
}

const fetchAlerts = async () => {
  let end = new Date()
  let start = new Date()

  if(queryRange.value !=0)
    localStorage.setItem('query_range', queryRange.value)

  switch(queryRange.value) {
    case 0:
        if(queryDtRange.value.length) {
          end = queryDtRange.value[1]
          start = queryDtRange.value[0]
        }
        break
    case '1':
        start.setDate(start.getDate() - 1)
        break
    case '2':
        start.setDate(start.getDate() - 7)
        break
    case '3':
        start.setDate(start.getDate() - 31)
        break
    case '4':
        start.setDate(start.getDate() - 1800)
        break
  }

  loading.value = true
  const fts_query = ftsSearch.value.replace(/:/g, '<2>')
  let params = {
    end: start.toISOString(),
    start: end.toISOString(),
    fts: encodeURIComponent(fts_query),
    offset: (currentPage.value - 1) * pageSize.value,
    limit: pageSize.value,
    history: historyMode.value
  }
  let res = await GetAlerts(params)
  alertsTable.value = res.alerts || {}
  total.value = res.total || res.alerts.length
  loading.value = false
}

const onPageChange = (newPage) => {
  currentPage.value = newPage
  fetchAlerts()
}

const onSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  fetchAlerts()
}

async function onAck(alert, current_status) {
  const user = userID.value;
  let new_status, hist_status, hist_update, comment = ''

  if (current_status !== ALERT_STATUS.ACKED) {
    [new_status, comment, hist_status, hist_update] = [ALERT_STATUS.ACKED, `Acknowledged by ${user}`, ALERT_STATUS.ACKED, true]
  } else {
    const res = await GetAlertHistory(alert, 10)
    new_status = res?.alert_history?.find(item => item.status === ALERT_STATUS.RESOLVED || item.status === ALERT_STATUS.FIRING)?.status ?? ALERT_STATUS.RESOLVED;
    [comment, hist_status, hist_update] = [`Ack removed by ${user}`, "unacked", true]
  }

  const result = await SetAlertStatus({
    alert_id: alert,
    status: new_status,
    comment: comment,
    history_status: hist_status,
    update_history: hist_update
  });

  if (result?.msg === "ok") {
    console.log(`Set ${alert} to ${new_status} OK`)
    if (expandedRowKeys.value?.length > 0 && expandedRowKeys.value[0] === alert) {
      alertHistory.value.unshift({"_id": 1, "timestamp": new Date().toISOString(), "alert_id": alert, "status": hist_status, "comment": comment})
    }
    fetchAlerts()
  } else {
    console.error(`Set ${alert} to ${new_status} ERROR`)
  }
}

async function onMute(alert, current_status) {
  const user = userID.value;
  let new_status, hist_status, hist_update, comment = ''

  if (current_status !== ALERT_STATUS.MUTED) {
    [new_status, hist_status, comment, hist_update] = [ALERT_STATUS.MUTED, ALERT_STATUS.MUTED, `Muted by ${user}`, true]
  } else {
    const res = await GetAlertHistory(alert, 10);
    new_status = res?.alert_history?.find(item =>item.status === ALERT_STATUS.RESOLVED || item.status === ALERT_STATUS.FIRING)?.status ?? ALERT_STATUS.RESOLVED;
    [hist_status, comment, hist_update] = [ALERT_STATUS.UNMUTED, `Mute removed by ${user}`, true]
  }

  const result = await SetAlertStatus({
    alert_id: alert,
    status: new_status,
    comment: comment,
    history_status: hist_status,
    update_history: hist_update
  });

  if (result?.msg === "ok") {
    console.log(`Set ${alert} to ${new_status} OK`);
    if (expandedRowKeys.value?.length > 0 && expandedRowKeys.value[0] === alert) {
      alertHistory.value.unshift({"_id": 1, "timestamp": new Date().toISOString(), "alert_id": alert, "status": hist_status, "comment": comment})
    }
    fetchAlerts();
  } else {
    console.error(`Set ${alert} to ${new_status} ERROR`);
  }
}

async function onDeleteAlert(alert) {
  const result = await DeleteAlert(alert)
  if (result?.msg === "ok") {
    ElMessage.success('Alert deleted')
    fetchAlerts()
  } else {
    ElMessage.error('Alert delete error')
  }
}

const fetchSearchFilters = async () => {
        let res = await SearchLoad()
        searchFilters.value = res
}

/* alerts handling over ws */
function upsertAlert(alert) {
  const index = alertsTable.value.findIndex(a => a.alert_id === alert.alert_id)
  if (index !== -1) {
    alertsTable.value[index] = alert
  } else {
    alertsTable.value.push(alert)
  }
}

function flushAlertsBuffer() {
  if (alertsBuffer.length === 0) return
  for (const alert of alertsBuffer) {
    const index = alertsTable.value.findIndex(a => a.alert_id === alert.alert_id)
    if (index !== -1) {
      if (alert.status !== ALERT_STATUS.RESOLVED) {
        alertsTable.value[index] = { ...alertsTable.value[index], ...alert }
        if (expandedRowKeys.value?.length > 0 && expandedRowKeys.value[0] === alert.alert_id) {
            alertHistory.value.unshift({"id": 1, "timestamp": alert.startsAt, "alert_id": alert.alert_id, "status": alert.status, "comment":""})
        }
      } else {
        alertsTable.value.splice(index, 1)
      }
    } else {
      if (alert.status !== ALERT_STATUS.RESOLVED)
        alertsTable.value.push(alert)
      //const todayISO = new Date().toISOString().slice(0, 10)
      //const alertISO = alert.startsAt.slice(0, 10)
      //if (todayISO === alertISO) 
    }
  }
  alertsTable.value.sort((a, b) => new Date(b.startsAt) - new Date(a.startsAt))
  alertsBuffer = []
  alertsBufferFlushTimer = null
}

/* websockets handler */
function wsHandler() {
  socket.on("connect", () => {
    console.log("Backend ws connected..")
    ws_state.connected = true
  })

  socket.on("disconnect", () => {
    console.log("Backend ws disconnected..")
    ws_state.connected = false
  })

  socket.on("alert_update", (msg) => {
    if (realTimeUpdate.value && !historyMode.value) {
      //console.log(msg)
      const _alert = msg?.data
      if (!_alert?.alert_id) return
      alertsBuffer.push(_alert)
      if (!alertsBufferFlushTimer) {
        alertsBufferFlushTimer = setTimeout(flushAlertsBuffer, 100)
      }
    }})
}

async function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      ElMessage.success(`Copied to clipboard!`)
      return navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement("textarea")
      textarea.value = text
      textarea.style.position = "fixed"
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      try {
        document.execCommand("copy")
        ElMessage.success(`Copied to clipboard!`)
      } catch (err) {
        ElMessage.error(`Failed copy to clipboard`)
      }
      document.body.removeChild(textarea)
    }
}

onMounted(async () => {
  ftsSearch.value = localStorage.getItem('fts_query') || ''
  const query_alert_id = route.params.alert_id || null
  if (query_alert_id) {
    ftsSearch.value = query_alert_id
    console.log(`Loading alert with ID ${query_alert_id}`)
  }
  fetchAlerts()
  fetchSearchFilters()
  wsHandler()
})

onBeforeUnmount(() => {
  socket.disconnect()
})
</script>

<style scoped>
.el-descriptions {
  margin-top: 1px;
}
.margin-top {
  margin-top: 10px;
}

.query-radio {
    margin-top: -1px;
    text-align: right;
    padding-right: 10px;
    overflow: auto;
}

.timespan-mobile {
    margin-top: -2px;
    padding-left: 10px;
    overflow: hidden;
}
.alert-details {
    padding-left: 55px;
    overflow: auto;
}

.lalert-details {
    background-color: rgb(54, 53, 77);
    width: 1000px;
    height: 400px;
    padding: 20px;
    border-radius: 5px;
    box-shadow: 2px 2px 5px rgb(54, 53, 77);
    overflow: auto;
}

.mobile-layout {
  --el-main-padding: 2px;
}

</style>
