import pandas as pd
from typing import List
from sqlalchemy import RowMapping
from icm.constants import (
    InterfaceField,
    ChangeField,
    ChangeAssignField,
    AssignmentCompleteField,
    StatisticsField,
)
from icm.utils import log
from icm.access.models.assignment import StatisticsModel
from icm.access.models.user import UserModel
from icm.data import AssignmentSchema, ChangeSchema, InterfaceSchema, UserSchema


class AdapterInterface:
    """Class to manage interface adapter."""

    @staticmethod
    def response(response_db: List[InterfaceSchema]) -> pd.DataFrame:
        """Adapt ORM rows to a DataFrame.

        Parameters
        ----------
        response_db : List[InterfaceSchema]
            Rows returned by the ORM.

        Returns
        -------
        pd.DataFrame
            Response adapted.
        """
        header = [
            InterfaceField.IP,
            InterfaceField.COMMUNITY,
            InterfaceField.SYSNAME,
            InterfaceField.IFINDEX,
            InterfaceField.IFNAME,
            InterfaceField.IFDESCR,
            InterfaceField.IFALIAS,
            InterfaceField.IFHIGHSPEED,
            InterfaceField.IFOPERSTATUS,
            InterfaceField.IFADMINSTATUS,
            InterfaceField.CONSULTED_AT,
        ]
        try:
            if not response_db:
                return pd.DataFrame(columns=header)
            response = pd.DataFrame(
                [
                    {
                        InterfaceField.ID: row.id,
                        InterfaceField.IP: row.ip,
                        InterfaceField.COMMUNITY: row.community,
                        InterfaceField.SYSNAME: row.sysname,
                        InterfaceField.IFINDEX: row.ifIndex,
                        InterfaceField.IFNAME: row.ifName,
                        InterfaceField.IFDESCR: row.ifDescr,
                        InterfaceField.IFALIAS: row.ifAlias,
                        InterfaceField.IFHIGHSPEED: row.ifHighSpeed,
                        InterfaceField.IFOPERSTATUS: row.ifOperStatus,
                        InterfaceField.IFADMINSTATUS: row.ifAdminStatus,
                        InterfaceField.CONSULTED_AT: row.consulted_at,
                    }
                    for row in response_db
                ]
            )
            response[InterfaceField.ID] = response[InterfaceField.ID].astype(str)
            response[InterfaceField.IP] = response[InterfaceField.IP].astype(str)
            response[InterfaceField.CONSULTED_AT] = response[
                InterfaceField.CONSULTED_AT
            ].astype(str)
            return response
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface adapter error. Failed to adapt response. {error}")
            return pd.DataFrame(columns=header)


class AdapterUser:
    """Class to manage user adapter."""

    @staticmethod
    def response(response_db: List[UserSchema]) -> List[UserModel]:
        """Adapt ORM rows to a model.

        Parameters
        ----------
        response_db : List[UserSchema]
            Rows returned by the ORM.

        Returns
        -------
        List[UserModel]
            Response adapted.
        """
        try:
            response = []
            for row in response_db:
                if row:
                    response.append(
                        UserModel(
                            username=row.username,
                            password=row.password,
                            name=row.name,
                            lastname=row.lastname,
                            status=row.status,
                            role=row.role,
                            created_at=row.created_at.strftime("%Y-%m-%d")
                            if row.created_at
                            else None,
                            updated_at=row.updated_at.strftime("%Y-%m-%d")
                            if row.updated_at
                            else None,
                        )
                    )
            return response
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User adapter error. Failed to adapt response. {error}")
            return []


class AdapterChange:
    """Class to manage change adapter."""

    @staticmethod
    def response(response_db: List[ChangeSchema]) -> List[dict]:
        """Adapt ORM rows to a model.

        Parameters
        ----------
        response_db : List[ChangeSchema]
            Rows returned by the ORM.

        Returns
        -------
        List[dict]
            Response adapted.
        """
        try:
            return [
                {
                    ChangeField.ID_OLD: row.id_old,
                    ChangeField.IP_OLD: row.ip_old,
                    ChangeField.COMMUNITY_OLD: row.community_old,
                    ChangeField.SYSNAME_OLD: row.sysname_old,
                    ChangeField.IFINDEX_OLD: row.ifIndex_old,
                    ChangeField.IFNAME_OLD: row.ifName_old,
                    ChangeField.IFDESCR_OLD: row.ifDescr_old,
                    ChangeField.IFALIAS_OLD: row.ifAlias_old,
                    ChangeField.IFHIGHSPEED_OLD: row.ifHighSpeed_old,
                    ChangeField.IFOPERSTATUS_OLD: row.ifOperStatus_old,
                    ChangeField.IFADMINSTATUS_OLD: row.ifAdminStatus_old,
                    ChangeField.ID_NEW: row.id_new,
                    ChangeField.IP_NEW: row.ip_new,
                    ChangeField.COMMUNITY_NEW: row.community_new,
                    ChangeField.SYSNAME_NEW: row.sysname_new,
                    ChangeField.IFINDEX_NEW: row.ifIndex_new,
                    ChangeField.IFNAME_NEW: row.ifName_new,
                    ChangeField.IFDESCR_NEW: row.ifDescr_new,
                    ChangeField.IFALIAS_NEW: row.ifAlias_new,
                    ChangeField.IFHIGHSPEED_NEW: row.ifHighSpeed_new,
                    ChangeField.IFOPERSTATUS_NEW: row.ifOperStatus_new,
                    ChangeField.IFADMINSTATUS_NEW: row.ifAdminStatus_new,
                    ChangeAssignField.USERNAME: row.assigned_user.username
                    if row.assigned_user
                    else None,
                    ChangeAssignField.NAME: row.assigned_user.name
                    if row.assigned_user
                    else None,
                    ChangeAssignField.LASTNAME: row.assigned_user.lastname
                    if row.assigned_user
                    else None,
                }
                for row in response_db
            ]
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change adapter error. Failed to adapt response. {error}")
            return []


class AdapterAssignment:
    """Class to manage assignment adapter."""

    @staticmethod
    def response(response_db: List[AssignmentSchema]) -> pd.DataFrame:
        """Adapt ORM rows to a DataFrame.

        Parameters
        ----------
        response_db : List[AssignmentSchema]
            Rows returned by the ORM, with `old_interface`, `current_interface`
            and `user` eagerly loaded.

        Returns
        -------
        pd.DataFrame
            Response adapted.
        """
        header = [
            AssignmentCompleteField.ID_OLD,
            AssignmentCompleteField.IP_OLD,
            AssignmentCompleteField.COMMUNITY_OLD,
            AssignmentCompleteField.SYSNAME_OLD,
            AssignmentCompleteField.IFINDEX_OLD,
            AssignmentCompleteField.IFNAME_OLD,
            AssignmentCompleteField.IFDESCR_OLD,
            AssignmentCompleteField.IFALIAS_OLD,
            AssignmentCompleteField.IFHIGHSPEED_OLD,
            AssignmentCompleteField.IFOPERSTATUS_OLD,
            AssignmentCompleteField.IFADMINSTATUS_OLD,
            AssignmentCompleteField.ID_NEW,
            AssignmentCompleteField.IP_NEW,
            AssignmentCompleteField.COMMUNITY_NEW,
            AssignmentCompleteField.SYSNAME_NEW,
            AssignmentCompleteField.IFINDEX_NEW,
            AssignmentCompleteField.IFNAME_NEW,
            AssignmentCompleteField.IFDESCR_NEW,
            AssignmentCompleteField.IFALIAS_NEW,
            AssignmentCompleteField.IFHIGHSPEED_NEW,
            AssignmentCompleteField.IFOPERSTATUS_NEW,
            AssignmentCompleteField.IFADMINSTATUS_NEW,
            AssignmentCompleteField.USERNAME,
            AssignmentCompleteField.NAME,
            AssignmentCompleteField.LASTNAME,
            AssignmentCompleteField.ASSIGN_BY,
            AssignmentCompleteField.TYPE_STATUS,
            AssignmentCompleteField.CREATED_AT,
            AssignmentCompleteField.UPDATED_AT,
        ]
        try:
            if not response_db:
                return pd.DataFrame(columns=header)
            response = pd.DataFrame(
                [
                    {
                        AssignmentCompleteField.ID_OLD: row.old_interface.id,
                        AssignmentCompleteField.IP_OLD: row.old_interface.ip,
                        AssignmentCompleteField.COMMUNITY_OLD: row.old_interface.community,
                        AssignmentCompleteField.SYSNAME_OLD: row.old_interface.sysname,
                        AssignmentCompleteField.IFINDEX_OLD: row.old_interface.ifIndex,
                        AssignmentCompleteField.IFNAME_OLD: row.old_interface.ifName,
                        AssignmentCompleteField.IFDESCR_OLD: row.old_interface.ifDescr,
                        AssignmentCompleteField.IFALIAS_OLD: row.old_interface.ifAlias,
                        AssignmentCompleteField.IFHIGHSPEED_OLD: row.old_interface.ifHighSpeed,
                        AssignmentCompleteField.IFOPERSTATUS_OLD: row.old_interface.ifOperStatus,
                        AssignmentCompleteField.IFADMINSTATUS_OLD: row.old_interface.ifAdminStatus,
                        AssignmentCompleteField.ID_NEW: row.current_interface.id,
                        AssignmentCompleteField.IP_NEW: row.current_interface.ip,
                        AssignmentCompleteField.COMMUNITY_NEW: row.current_interface.community,
                        AssignmentCompleteField.SYSNAME_NEW: row.current_interface.sysname,
                        AssignmentCompleteField.IFINDEX_NEW: row.current_interface.ifIndex,
                        AssignmentCompleteField.IFNAME_NEW: row.current_interface.ifName,
                        AssignmentCompleteField.IFDESCR_NEW: row.current_interface.ifDescr,
                        AssignmentCompleteField.IFALIAS_NEW: row.current_interface.ifAlias,
                        AssignmentCompleteField.IFHIGHSPEED_NEW: row.current_interface.ifHighSpeed,
                        AssignmentCompleteField.IFOPERSTATUS_NEW: row.current_interface.ifOperStatus,
                        AssignmentCompleteField.IFADMINSTATUS_NEW: row.current_interface.ifAdminStatus,
                        AssignmentCompleteField.USERNAME: row.user.username,
                        AssignmentCompleteField.NAME: row.user.name,
                        AssignmentCompleteField.LASTNAME: row.user.lastname,
                        AssignmentCompleteField.ASSIGN_BY: row.assign_by,
                        AssignmentCompleteField.TYPE_STATUS: row.type_status,
                        AssignmentCompleteField.CREATED_AT: row.created_at,
                        AssignmentCompleteField.UPDATED_AT: row.updated_at,
                    }
                    for row in response_db
                ]
            )
            response[AssignmentCompleteField.ID_OLD] = response[
                AssignmentCompleteField.ID_OLD
            ].astype(str)
            response[AssignmentCompleteField.IP_OLD] = response[
                AssignmentCompleteField.IP_OLD
            ].astype(str)
            response[AssignmentCompleteField.ID_NEW] = response[
                AssignmentCompleteField.ID_NEW
            ].astype(str)
            response[AssignmentCompleteField.IP_NEW] = response[
                AssignmentCompleteField.IP_NEW
            ].astype(str)
            response[AssignmentCompleteField.CREATED_AT] = response[
                AssignmentCompleteField.CREATED_AT
            ].astype(str)
            response[AssignmentCompleteField.UPDATED_AT] = response[
                AssignmentCompleteField.UPDATED_AT
            ].astype(str)
            return response
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment adapter error. Failed to adapt response. {error}")
            return pd.DataFrame(columns=header)

    @staticmethod
    def response_statistics(response_db: List[RowMapping]) -> List[StatisticsModel]:
        """Adapt aggregated query rows to a model.

        Parameters
        ----------
        response_db : List[RowMapping]
            Rows returned by the statistics aggregate query, one per username.

        Returns
        -------
        List[StatisticsModel]
            Response adapted.
        """
        try:
            response: List[StatisticsModel] = []
            for row in response_db:
                if row:
                    response.append(
                        StatisticsModel(
                            total_pending_today=row[StatisticsField.TOTAL_PENDING_TODAY],
                            total_inspected_today=row[StatisticsField.TOTAL_INSPECTED_TODAY],
                            total_rediscovered_today=row[StatisticsField.TOTAL_REDISCOVERED_TODAY],
                            total_pending_month=row[StatisticsField.TOTAL_PENDING_MONTH],
                            total_inspected_month=row[StatisticsField.TOTAL_INSPECTED_MONTH],
                            total_rediscovered_month=row[StatisticsField.TOTAL_REDISCOVERED_MONTH],
                            username=row[StatisticsField.USERNAME],
                            name=row[StatisticsField.NAME],
                            lastname=row[StatisticsField.LASTNAME],
                        )
                    )
            return response
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment adapter error. Failed to adapt response. {error}")
            return []
