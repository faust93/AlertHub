<template>
<div style="padding: 30px;">
  <h4>Alert Analytics</h4><br/>
  <el-row :gutter="16">
    <el-col :span="2">
      <div class="statistic-card">
        <el-statistic :value="FiringTotal">
          <template #title>
            <div style="display: inline-flex; align-items: center">
              🔥 Firing Alerts
            </div>
          </template>
        </el-statistic>
      </div>
    </el-col>
    <el-col :span="2">
      <div class="statistic-card">
        <el-statistic :value="ResolvedTotal">
          <template #title>
            <div style="display: inline-flex; align-items: center">
             ✅ Resolved Alerts
            </div>
          </template>
        </el-statistic>
      </div>
    </el-col>
    <el-col :span="2">
      <div class="statistic-card">
        <el-statistic :value="AckedTotal">
          <template #title>
            <div style="display: inline-flex; align-items: center">
            👁️ Acked Alerts
            </div>
          </template>
        </el-statistic>
      </div>
    </el-col>
    <el-col :span="2">
      <div class="statistic-card">
        <el-statistic :value="MutedTotal">
          <template #title>
            <div style="display: inline-flex; align-items: center">
            🔕 Muted Alerts
            </div>
          </template>
        </el-statistic>
      </div>
    </el-col>
  </el-row>
  <br/>
  <el-row :gutter="20">
    <el-col :span="4">
      <el-card style="max-width: 280px" >
           <PieChart :chartData="severityData" :options="severityOptions" />
      </el-card>
    </el-col>
    <el-col :span="12">
      <el-card style="max-width: 880px" >
      <el-table :data="alertNameData" stripe show-summary sum-text="Total" size="small" style="overflow: auto; width: 100%; height: calc(30vh);">
        <el-table-column label="Alert Name" prop="name" width="500">
          <template #default="scope">
            {{ scope.row.name }}
          </template>
        </el-table-column>
        <el-table-column label="Severity" prop="severity" sortable>
          <template #default="scope">
            {{ scope.row.severity }}
          </template>
        </el-table-column>
        <el-table-column label="Total" prop="total" sortable align="center">
          <template #default="scope">
            <el-text tag="b" size="small">{{ scope.row.total }}</el-text>
          </template>
        </el-table-column>
      </el-table>
      </el-card>
    </el-col>
  </el-row>
</div>
</template>

<script setup>
import { onBeforeUnmount, ref, onMounted, computed } from 'vue'
import { PieChart } from 'vue-chart-3'
import { Chart, registerables } from "chart.js"
import { GetAlertStats } from '@/request/api.js'
import { ALERT_STATUS, ALERT_SEVERITY } from '@/utils/constants'

Chart.register(...registerables)

const statusData = ref([])
const alertNameData = ref([])
const severityData = ref({
  labels: [ALERT_SEVERITY.CRITICAL, ALERT_SEVERITY.WARNING, ALERT_SEVERITY.INFO],
   datasets: [
     {
       data: [10, 10, 5],
       backgroundColor: ['#f56c6c', '#e6a23c', '#d4d4d5'],
     },
    ],
})

const severityOptions = ref({
  responsive: true,
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        color: '#374151',
        font: {
          size: 12,
        }
      }
    },
    title: {
      display: true,
      text: 'Alerts Severity',
      font: {
        size: 14
      }
    }
  }
})

let StatsFlushTimer = null

const AckedTotal = computed(() => {
  let total = statusData.value?.find(item => item.status === ALERT_STATUS.ACKED)?.total ?? 0
  return total
})

const MutedTotal = computed(() => {
  let total = statusData.value?.find(item => item.status === ALERT_STATUS.MUTED)?.total ?? 0
  return total
})

const FiringTotal = computed(() => {
  let total = statusData.value?.find(item => item.status === ALERT_STATUS.FIRING)?.total ?? 0
  return total
})

const ResolvedTotal = computed(() => {
  let total = statusData.value?.find(item => item.status === ALERT_STATUS.RESOLVED)?.total ?? 0
  return total
})

async function fetchAlertStatuses() {
  const { status, alert_name, severity } = await GetAlertStats()
  statusData.value = status
  alertNameData.value = alert_name
  severityData.value.datasets[0].data[0] = severity?.find(item => item.severity === ALERT_SEVERITY.CRITICAL)?.total ?? 0
  severityData.value.datasets[0].data[1] = severity?.find(item => item.severity === ALERT_SEVERITY.WARNING)?.total ?? 0
  severityData.value.datasets[0].data[2] = severity?.find(item => item.severity === ALERT_SEVERITY.INFO)?.total ?? 0
}

function flushStats() {
  console.log("Flushing stats")
  clearTimeout(StatsFlushTimer)
  fetchAlertStatuses()
  StatsFlushTimer = setTimeout(flushStats, 60000)
}

onMounted(async () => {
  fetchAlertStatuses()
  StatsFlushTimer = setTimeout(flushStats, 60000)  
})

onBeforeUnmount(() => {
  clearTimeout(StatsFlushTimer)
})
</script>

<style scoped>
.el-statistic {
  --el-statistic-content-font-size: 24px;
}

.statistic-card {
  padding: 10px;
  border-radius: 4px;
  background-color: var(--el-bg-color-overlay);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  box-shadow: 0px 0px 12px rgba(0,0,0,0.12);
}
</style>