<template>
  <div class="time-grid">
    <div class="controls" v-if="showControls">
      <button @click="scrollToNow" class="now-btn">Now</button>
      <label v-if="allowZoom">
        Zoom:
        <input
          type="range"
          min="30"
          max="400"
          step="10"
          v-model="dayWidth"
        />
      </label>
    </div>

    <div
      class="timeline-container"
      ref="timelineContainer">
      <div
        class="timeline"
        ref="timeline"
        @wheel="handleWheel"
        @mousedown="onMouseDown"
        @scroll="onScroll">
        <!-- Virtualized Days Container -->
        <div 
          class="days-container"
          :style="{ width: totalWidth + 'px' }">

          <!-- Only render visible days -->
          <div
            v-for="day in visibleDays"
            :key="day.date.getTime()"
            class="day-cell"
            :class="{ today: isToday(day.date) }"
            :style="{ 
              left: getDateOffset(day.date) + 'px',
              width: dayWidth + 'px'
            }">
            <div class="day-label">
              <span v-if="dayWidth >= 40">
                {{ day.label }}
                <span v-if="day.isFirstOfMonth"  class="month-label">
                {{ day.month }}
                </span>
              </span>
              <span v-else="dayWidth <= 34">
                {{ day.label.substr(0,2) }}
                <span 
                  v-if="day.isFirstOfMonth" 
                  class="month-label">
                  {{ day.month }}
                </span>
              </span>
            </div>
            
            <!-- Hour ticks -->
            <div class="hour-ticks" v-if="dayWidth >= 120">
              <div 
                v-for="tick in hourTicks" 
                :key="`${day.date.getTime()}-tick-${tick}`"
                class="hour-tick"
                :style="{ left: (tick * hourWidth) + 'px' }"
              >
              <span 
                  v-if="tick % 6 === 0" 
                  class="hour-label">
                  {{ String(tick).padStart(2, '0') }}:00
              </span>
            </div>
            </div>
          </div>
        </div>
        
        <!-- Grid Lines (only visible range) -->
        <div class="grid" :style="{ width: totalWidth + 'px', height: timelineHeight + 'px' }">
          <!-- Day lines -->
          <template v-for="day in visibleDays" :key="`line-${day.date.getTime()}`">
            <div 
              class="grid-line day-line"
              :style="{ left: getDateOffset(day.date) + 'px' }"
            ></div>
            
            <!-- Hour lines -->
            <template v-if="dayWidth >= 120">
              <div 
                v-for="tick in hourTicks"
                :key="`hour-${day.date.getTime()}-${tick}`"
                class="grid-line hour-line"
                :style="{ left: (getDateOffset(day.date) + tick * hourWidth) + 'px' }">
              </div>
            </template>
          </template>
          
          <!-- Group lines and headers with dynamic positioning -->
          <template v-for="(group, index) in groupedEventsWithPlacement" :key="`group-${index}`">
            <div 
              class="grid-line group-line"
              :style="{ 
                top: (50 + getGroupTopPosition(index)) + 'px', 
                width: totalWidth + 'px' 
              }"
            ></div>
            <div 
              class="group-header"
              :style="{
                top: (50 + getGroupTopPosition(index)) + 'px',
                height: groupHeaderHeight + 'px',
                lineHeight: groupHeaderHeight + 'px'
              }">
              {{ group.name }}
            </div>
          </template>
          
          <!-- Track lines within groups -->
          <div 
            v-for="line in trackLines" 
            :key="'track-' + line.index" 
            class="grid-line track-line"
            :style="{ 
              top: (50 + line.top) + 'px', 
              width: totalWidth + 'px' 
            }"
          ></div>
        </div>
        
        <!-- Events (only visible range) -->
        <div class="events-container" :style="{ height: timelineHeight + 'px' }">
          <div
            v-for="event in visibleEvents"
            :key="event.id || (event.title + event.start.getTime())"
            class="event-bar"
            :style="getEventStyle(event)"
            :title="event.title + ' — ' + formatEventRange(event)"
            @click="$emit('event-click', event)"
          >
            {{ event.title }}
          </div>
        </div>
        
        <!-- Today line -->
        <div 
          class="today-line" 
          :style="{ left: nowOffset + 'px', height: timelineHeight + 'px' }"
          v-if="showTodayLine"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { format, addDays, isSameDay } from "date-fns";
import { debounce } from 'lodash-es';

// Define props
const props = defineProps({
  events: {
    type: Array,
    default: () => []
  },
  startDate: {
    type: Date,
    required: true
  },
  endDate: {
    type: Date,
    required: true
  },
  initialDayWidth: {
    type: Number,
    default: 70
  },
  trackHeight: {
    type: Number,
    default: 32
  },
  showControls: {
    type: Boolean,
    default: true
  },
  allowZoom: {
    type: Boolean,
    default: true
  },
  showTodayLine: {
    type: Boolean,
    default: true
  },
  now: {
    type: Date,
    default: () => new Date()
  },
  groups: {
    type: Array,
    default: () => []
  },
  groupHeaderHeight: {
    type: Number,
    default: 25
  }
});

// Define emits
const emit = defineEmits(['event-click', 'scroll', 'zoom']);

// Refs
const timeline = ref(null);
const timelineContainer = ref(null);

// Zoom & Dimensions
const { dayWidth, hourWidth, minuteWidth } = useTimelineZoom(props.initialDayWidth);

// Days computation
const days = computed(() => {
  const result = [];
  let cur = new Date(props.startDate);
  while (cur <= props.endDate) {
    result.push({
      date: new Date(cur),
      label: format(cur, "dd.MM"),
      month: format(cur, "MMM"),
      isFirstOfMonth: cur.getDate() === 1
    });
    cur = addDays(cur, 1);
  }
  return result;
});

const hourTicks = Array.from({ length: 24 }, (_, i) => i);
const totalWidth = computed(() => days.value.length * dayWidth.value);

// Calculate total timeline height based on all groups
const timelineHeight = computed(() => {
  const totalGroupsHeight = groupedEventsWithPlacement.value.reduce((total, group) => {
    return total + group.height;
  }, 0);
  return 50 + totalGroupsHeight; // 50px for days header + groups height
});

// Virtualization - visible range
const visibleRange = ref({ start: 0, end: 50 });
const visibleDays = computed(() => {
  return days.value.slice(
    visibleRange.value.start, 
    visibleRange.value.end
  );
});

// Group events by group property and calculate placement
const groupedEventsWithPlacement = computed(() => {
  if (!props.groups || props.groups.length === 0) {
    // Handle case with no groups - put all events in one group
    const placementResult = useTimelineEventsForGroup(
      props.events, 
      props.startDate, 
      props.endDate
    );
    const placedEvents = placementResult.placedEvents;
    const maxTrack = placementResult.maxTrack;
    
    return [{
      name: 'All Events',
      id: 'all',
      events: props.events,
      placedEvents: placedEvents,
      maxTrack: maxTrack,
      height: props.groupHeaderHeight + ((maxTrack + 1) * props.trackHeight)
    }];
  }
  
  // Process each group with its events
  return props.groups.map(group => {
    const groupEvents = props.events.filter(event => event.groupId === group.id);
    const placementResult = useTimelineEventsForGroup(
      groupEvents, 
      props.startDate, 
      props.endDate
    );
    const placedEvents = placementResult.placedEvents;
    const maxTrack = placementResult.maxTrack;
    
    return {
      name: group.name,
      id: group.id,
      events: groupEvents,
      placedEvents: placedEvents,
      maxTrack: maxTrack,
      height: props.groupHeaderHeight + ((maxTrack + 1) * props.trackHeight)
    };
  });
});

// Calculate cumulative group heights for positioning
const cumulativeGroupHeights = computed(() => {
  const heights = [0]; // Start with 0 for the first group
  let cumulative = 0;
  
  groupedEventsWithPlacement.value.forEach((group, index) => {
    if (index < groupedEventsWithPlacement.value.length - 1) {
      cumulative += group.height;
      heights.push(cumulative);
    }
  });
  
  return heights;
});

// Get top position for a group by index
function getGroupTopPosition(groupIndex) {
  return cumulativeGroupHeights.value[groupIndex] || 0;
}

// Calculate track lines for grid with dynamic positioning
const trackLines = computed(() => {
  const lines = [];
  
  groupedEventsWithPlacement.value.forEach((group, groupIndex) => {
    const groupTop = getGroupTopPosition(groupIndex);
    const tracksTop = groupTop + props.groupHeaderHeight;
    
    // Add track lines within the group
    for (let trackIndex = 0; trackIndex <= group.maxTrack; trackIndex++) {
      lines.push({
        index: `group-${groupIndex}-track-${trackIndex}`,
        top: tracksTop + ((trackIndex + 1) * props.trackHeight)
      });
    }
  });
  
  return lines;
});

const visibleEvents = computed(() => {
  if (!timeline.value) return [];
  
  const containerWidth = timeline.value.clientWidth;
  const scrollLeft = timeline.value.scrollLeft;
  
  const startIndex = Math.floor(scrollLeft / dayWidth.value);
  const endIndex = Math.ceil((scrollLeft + containerWidth) / dayWidth.value);
  
  const visibleStart = new Date(days.value[Math.max(0, startIndex - 5)]?.date || props.startDate);
  const visibleEnd = new Date(days.value[Math.min(days.value.length - 1, endIndex + 5)]?.date || props.endDate);
  
  // Flatten all placed events from groups
  const allPlacedEvents = groupedEventsWithPlacement.value.flatMap(group => {
    if (Array.isArray(group.placedEvents)) {
      return group.placedEvents.map(event => ({
        ...event,
        groupId: group.id
      }));
    }
    return [];
  });
  
  return allPlacedEvents.filter(event => 
    event.start <= visibleEnd && event.end >= visibleStart
  );
});

// Event styling with dynamic group positioning
function getEventStyle(event) {
  const offsetMinutes = (event.start - props.startDate) / (1000 * 60);
  const widthMinutes = (event.end - event.start) / (1000 * 60);
  
  const leftPx = offsetMinutes * minuteWidth.value;
  const widthPx = Math.max(2, widthMinutes * minuteWidth.value);
  
  // Find which group this event belongs to
  const groupInfo = groupedEventsWithPlacement.value.find(g => 
    g.id === event.groupId || (g.id === 'all' && !event.groupId)
  );
  const groupIndex = groupedEventsWithPlacement.value.indexOf(groupInfo);
  
  // Calculate top position based on group and track
  let topOffset = 50; // Base offset for days header
  if (groupIndex >= 0) {
    topOffset += getGroupTopPosition(groupIndex);
    topOffset += props.groupHeaderHeight; // Skip group header
  }
  if (event.track !== undefined) {
    topOffset += event.track * props.trackHeight;
  }
  
  return {
    left: Math.round(leftPx) + "px",
    width: Math.round(widthPx) + "px",
    top: topOffset + "px",
    backgroundColor: event.color,
    position: "absolute"
  };
}

// Date helpers
function getDateOffset(date) {
  return ((date - props.startDate) / 86400000) * dayWidth.value;
}

function isToday(date) {
  return isSameDay(date, props.now);
}

// Today line
const nowOffset = computed(() => {
  const offsetMinutes = (props.now - props.startDate) / (1000 * 60);
  return Math.round(offsetMinutes * minuteWidth.value);
});

// Scroll handling
const { handleWheel, onMouseDown, scrollToNow } = useTimelineScroll(
  timeline, 
  dayWidth, 
  minuteWidth,
  computed(() => props.startDate),
  nowOffset
);

// Update visible range on scroll
function updateVisibleRange() {
  if (!timeline.value) return;
  
  const scrollLeft = timeline.value.scrollLeft;
  const containerWidth = timeline.value.clientWidth;
  
  const startIndex = Math.floor(scrollLeft / dayWidth.value);
  const endIndex = Math.ceil((scrollLeft + containerWidth) / dayWidth.value);
  
  visibleRange.value = {
    start: Math.max(0, startIndex - 10),
    end: Math.min(days.value.length, endIndex + 10)
  };
  
  // Emit scroll event
  emit('scroll', {
    scrollLeft,
    startIndex,
    endIndex,
    visibleStart: days.value[startIndex]?.date,
    visibleEnd: days.value[endIndex]?.date
  });
}

// Debounced scroll handler
const debouncedScroll = debounce(updateVisibleRange, 50);

function onScroll() {
  debouncedScroll();
}

// Event formatting
function formatEventRange(ev) {
  return `${format(ev.start, "yyyy-MM-dd HH:mm")} → ${format(ev.end, "yyyy-MM-dd HH:mm")}`;
}

// Lifecycle
onMounted(() => {
  updateVisibleRange();
});

// Watch for zoom changes
watch(dayWidth, (newWidth) => {
  nextTick(() => {
    updateVisibleRange();
  });
  emit('zoom', newWidth);
});

// Expose methods to parent
defineExpose({
  scrollToNow,
  scrollTo: (scrollLeft) => {
    if (timeline.value) {
      timeline.value.scrollLeft = scrollLeft;
    }
  },
  getScrollPosition: () => {
    return timeline.value ? timeline.value.scrollLeft : 0;
  }
});

function useTimelineScroll(timelineRef, dayWidth, minuteWidth, startDate, nowOffset) {
  let isDragging = false;
  let startX = 0;
  let scrollStart = 0;

  function handleWheel(e) {
    if (e.ctrlKey) {
      e.preventDefault();
      const rect = timelineRef.value.getBoundingClientRect();
      const cursorX = e.clientX - rect.left + timelineRef.value.scrollLeft;
      const oldWidth = dayWidth.value;
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      let newWidth = oldWidth * zoomFactor;

      newWidth = Math.max(30, Math.min(400, newWidth));

      const scale = newWidth / oldWidth;
      timelineRef.value.scrollLeft = cursorX * scale - (e.clientX - rect.left);
      dayWidth.value = newWidth;
    }
  }

  function onMouseDown(e) {
    isDragging = true;
    startX = e.pageX;
    scrollStart = timelineRef.value.scrollLeft;

    const onMouseMove = (e) => {
      if (!isDragging) return;
      e.preventDefault();
      const dx = e.pageX - startX;
      timelineRef.value.scrollLeft = scrollStart - dx;
    };

    const onMouseUp = () => {
      isDragging = false;
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  }

  function scrollToNow() {
    if (timelineRef.value) {
      timelineRef.value.scrollLeft = nowOffset.value - 200;
    }
  }

  return {
    handleWheel,
    onMouseDown,
    scrollToNow
  };
}

function useTimelineZoom(initialWidth = 70) {
  const dayWidth = ref(initialWidth);
  
  const hourWidth = computed(() => dayWidth.value / 24);
  const minuteWidth = computed(() => hourWidth.value / 60);
  
  return {
    dayWidth,
    hourWidth,
    minuteWidth
  };
}

// Event placement for a single group of events
function useTimelineEventsForGroup(events, startDate, endDate) {
  const placedEvents = events.map(ev => ({ ...ev })).sort((a, b) => a.start - b.start);
  const tracks = [];
  const out = [];

  for (const ev of placedEvents) {
    const event = { ...ev };
    let placed = false;

    for (let ti = 0; ti < tracks.length; ti++) {
      const last = tracks[ti][tracks[ti].length - 1];
      if (event.start.getTime() < last.end.getTime() && 
          event.end.getTime() > last.start.getTime()) {
        continue;
      } else {
        event.track = ti;
        tracks[ti].push(event);
        out.push(event);
        placed = true;
        break;
      }
    }

    if (!placed) {
      event.track = tracks.length;
      tracks.push([event]);
      out.push(event);
    }
  }

  const maxTrack = out.length > 0 ? Math.max(...out.map(ev => ev.track || 0), 0) : 0;

  return { placedEvents: out, maxTrack };
}
</script>

<style scoped>
.timeline {
  height: 100%;
  overflow-x: auto;
  overflow-y: auto;
  position: relative;
  cursor: grab;
  user-select: none;
  --day-cell-today-background: #fff3cd;
  --day-cell-today-border: #ffc107;
  --today-line-width: 1px;
}

.timeline:active {
  cursor: grabbing;
}

.time-grid {
  padding: 10px;
  box-sizing: border-box;
}

.controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.now-btn {
  padding: 4px 8px;
  cursor: pointer;
}

.timeline-container {
  border: 1px solid #ddd;
  height: 300px;
  overflow: hidden;
  background: #fff;
  position: relative;
}

.days-container {
  position: sticky;
  top: 0;
  z-index: 10;
  height: 50px;
}

.day-cell {
  position: absolute;
  border-right: 1px solid #eee;
  background: #f0efef;
  padding: 6px 4px;
  box-sizing: border-box;
  height: 45px;
}

.day-cell.today {
  background: var(--day-cell-today-background);
  border-color: var(--day-cell-today-border);
}

.day-label {
  font-size: 12px;
  text-align: center;
}

.month-label {
  font-weight: 600;
  font-size: 12px;
  display: block;
  margin-bottom: 4px;
}

.hour-ticks {
  position: absolute;
  top: 30px;
  left: 0;
  right: 0;
  height: 15px;
}

.hour-tick {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(0,0,0,0.1);
}

.grid {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 1;
}

.grid-line {
  position: absolute;
  box-sizing: border-box;
}

.day-line {
  top: 0;
  bottom: 0;
  border-left: 1px solid #ececec;
}

.hour-line {
  border-left: 1px dashed rgba(234,234,234,0.8);
}

.group-line {
  left: 0;
  border-top: 2px solid #333;
  z-index: 2;
}

.track-line {
  left: 0;
  border-top: 1px dashed #ddd;
}

.hour-label {
  font-size: 10px;
  position: absolute;
  top: 2px;
  left: 4px;
  color: #666;
  z-index: 2;
}

.group-header {
  position: absolute;
  left: 0;
  right: 0;
  background: #e9ecef;
  font-size: 14px;
  font-weight: normal;
  padding: 0 8px;
  box-sizing: border-box;
  border-bottom: 1px solid #ccc;
  z-index: 3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.events-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 5;
}

.event-bar {
  position: absolute;
  height: 26px;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  padding: 4px 8px;
  white-space: nowrap;
  box-sizing: border-box;
  will-change: left, width;
  pointer-events: auto;
  cursor: pointer;
}

.today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: var(--today-line-width);
  background: crimson;
  z-index: 20;
}
</style>