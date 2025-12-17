import instance from "./http.js";

export const loginAPI = (data) =>
    instance.post("/auth/login", data);

// Get all alerts
export const GetAlerts = (params) =>
    instance.get(`/api/v1/alertsRange?from=${params.start}&to=${params.end}&fts=${params.fts}&offset=${params.offset}&limit=${params.limit}&history=${params.history}`);

//export const GetAlerts = (params) =>
//    instance.get("/api/v1/alertsRange", {
//    params: {
//      from: params.start,
//      to: params.end,
//      fts: params.fts,
//      ...params.optArgs,
//    },
//});

// Get alert timeline
export const GetAlertHistory = (alId, limit) =>
    instance.get(`/api/v1/alertHistory?id=${alId}&limit=${limit ?? 100}`);

export const SetAlertStatus = (data) =>
    instance.post("/api/v1/setAlertStatus", data);

export const DeleteAlert = (aId) =>
    instance.get(`/api/v1/deleteAlert?id=${aId}`);

// Saved queries
export const SearchSave = (data) =>
    instance.post("/api/v1/searchSave", data);

export const SearchUpdate = (data) =>
    instance.post("/api/v1/searchUpdate", data);

export const SearchLoad = () =>
    instance.get("/api/v1/searchLoad");

export const SearchDelete = (sId) =>
    instance.get(`/api/v1/searchDelete?id=${sId}`);

// Users
export const GetUsers = () =>
    instance.get("/api/v1/getUsers");

export const AddUser = (data) =>
    instance.post("/api/v1/addUser", data);

export const UpdateUser = (data) =>
    instance.post("/api/v1/updateUser", data);

export const DeleteUser = (params) =>
    instance.get(`/api/v1/deleteUser?name=${params.name}&id=${params.id}`);

// Teams
export const GetTeams = () =>
    instance.get("/api/v1/getTeams");

export const AddTeam = (data) =>
    instance.post("/api/v1/addTeam", data);

export const DeleteTeam = (tId) =>
    instance.get(`/api/v1/deleteTeam?id=${tId}`);

export const UpdateTeam = (data) =>
    instance.post("/api/v1/updateTeam", data);

// Schedules
export const GetSchedules = () =>
    instance.get("/api/v1/getSchedules");

export const AddSchedule = (data) =>
    instance.post("/api/v1/addSchedule", data);

export const DeleteSchedule = (sid) =>
    instance.get(`/api/v1/deleteSchedule?id=${sid}`);

export const UpdateSchedule = (data) =>
    instance.post("/api/v1/updateSchedule", data);

// ScheduleGroups
export const GetScheduleGroups = () =>
    instance.get("/api/v1/getScheduleGroups");

export const AddScheduleGroup = (data) =>
    instance.post("/api/v1/addScheduleGroup", data);

export const DeleteScheduleGroup = (gid) =>
    instance.get(`/api/v1/deleteScheduleGroup?id=${gid}`);

export const UpdateScheduleGroup = (data) =>
    instance.post("/api/v1/updateScheduleGroup", data);

// Maintenance
export const GetMaintenances = () =>
    instance.get("/api/v1/getMaintenances");

export const AddMaintenance = (data) =>
    instance.post("/api/v1/addMaintenance", data);

export const DeleteMaintenance = (pid) =>
    instance.get(`/api/v1/deleteMaintenance?id=${pid}`);

export const UpdateMaintenance = (data) =>
    instance.post("/api/v1/updateMaintenance", data);

// Pipelines
export const GetPipelines = () =>
    instance.get("/api/v1/getPipelines");

export const AddPipeline = (data) =>
    instance.post("/api/v1/addPipeline", data);

export const DeletePipeline = (pid) =>
    instance.get(`/api/v1/deletePipeline?id=${pid}`);

export const UpdatePipeline = (data) =>
    instance.post("/api/v1/updatePipeline", data);

// Templates
export const GetTemplates = () =>
    instance.get("/api/v1/getTemplates");

export const GetTemplate = (tid) =>
    instance.get(`/api/v1/getTemplate?id=${tid}`);

export const AddTemplate = (data) =>
    instance.post("/api/v1/addTemplate", data);

export const DeleteTemplate = (tid) =>
    instance.get(`/api/v1/deleteTemplate?id=${tid}`);

export const UpdateTemplate = (data) =>
    instance.post("/api/v1/updateTemplate", data);

export const RenderTemplate = (data) =>
    instance.post("/api/v1/renderTemplate", data);

// Pipeline validation
export const ValidatePipeline = (data) =>
    instance.post("/api/v1/validatePipeline", data);

// Stats
export const GetAlertStats = () =>
    instance.get("/api/v1/alertStats");
