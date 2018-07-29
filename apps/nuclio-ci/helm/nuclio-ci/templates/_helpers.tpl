
{{- define "nuclio-ci.Name" -}}
{{- "nuclio-ci" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.buildPushArtifacts" -}}
{{- "build-push-artifacts" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.completeTest" -}}
{{- "complete-test" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.databaseInit" -}}
{{- "database-init" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.gatekeeper" -}}
{{- "gatekeeper" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.githubStatusUpdater" -}}
{{- "github-status-updater" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.releaseNode" -}}
{{- "release-node" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.runJob" -}}
{{- "run-job" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.runTestCase" -}}
{{- "run-test-case" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.slackNotifier" -}}
{{- "slack-notifier" | trunc 63 -}}
{{- end -}}

{{- define "nuclio-ci.serviceName" -}}
{{- "nuclio-ci-service" | trunc 63 -}}
{{- end -}}
